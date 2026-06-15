// remediateCheckmarx — agentic remediation step for an existing Jenkins
// Checkmarx (on-prem CxSAST) flow.
//
// It picks up where a fetch-report step leaves off: take the CxSAST XML report
// for a scan, normalize it with the portable DevSecOps scripts, have the agent
// remediate the findings, and raise a remediation PR on the code repo. It never
// pushes to the default branch — the PR-merge human gate is preserved.
//
// Usage (Jenkinsfile / job DSL), mirroring the shared-library style:
//
//   remediateCheckmarx {
//       code_repo        = 'https://github.com/your-org/your-service.git'
//       scan_id          = '12345'                 // Checkmarx scan id to fetch
//       checkmarx_url    = 'https://checkmarx.your-company.example'
//       devsecops_repo   = 'https://github.com/your-org/devsecops.git'
//       devsecops_ref    = 'v1'
//       agent_cmd        = 'python3 .devsecops/scripts/agents/bedrock-agent.py'
//   }
//
// Credentials expected on the Jenkins agent:
//   - checkmarx-creds   (username/password for the CxSAST REST API)
//   - github-credentials (to clone the code repo and the DevSecOps repo, and push the branch)
// plus credentials for whatever AGENT_CMD runtime you configure.

def call(body) {
    def config = [:]
    body.resolveStrategy = Closure.DELEGATE_FIRST
    body.delegate = config
    body()

    CODE_REPO       = config.code_repo
    SCAN_ID         = config.scan_id
    DEVSECOPS_REPO  = config.devsecops_repo
    DEVSECOPS_REF   = config.devsecops_ref ?: 'v1'
    AGENT_CMD       = config.agent_cmd ?: 'python3 .devsecops/scripts/agents/bedrock-agent.py'
    CHECKMARX_URL   = config.checkmarx_url   // required — no internal default
    DOWNSTREAM_JOBS = config.downstream_jobs ?: []

    if (!CODE_REPO)     error "remediateCheckmarx: 'code_repo' is required."
    if (!DEVSECOPS_REPO) error "remediateCheckmarx: 'devsecops_repo' is required."
    if (!CHECKMARX_URL) error "remediateCheckmarx: 'checkmarx_url' is required."

    pipeline {
        agent any
        options {
            buildDiscarder(logRotator(numToKeepStr: '5'))
            disableConcurrentBuilds()
            timeout(time: 60, unit: 'MINUTES')
        }
        environment {
            CX_URL = "${CHECKMARX_URL}"
        }
        stages {
            stage('checkout code repo') {
                steps {
                    dir('code-repo') {
                        git credentialsId: 'github-credentials', url: "${CODE_REPO}", branch: 'master'
                    }
                }
            }
            stage('load devsecops tooling') {
                steps {
                    dir('code-repo') {
                        // Portable scripts live in the DevSecOps product repo; clone at the
                        // pinned ref so the Jenkins side and the GitHub Actions side stay in sync.
                        sh "rm -rf .devsecops && git clone --depth 1 --branch ${DEVSECOPS_REF} ${DEVSECOPS_REPO} .devsecops"
                    }
                }
            }
            stage('fetch Checkmarx XML report') {
                steps {
                    dir('code-repo') {
                        withCredentials([usernamePassword(
                                credentialsId: 'checkmarx-creds',
                                usernameVariable: 'CX_USER',
                                passwordVariable: 'CX_PASS'
                        )]) {
                            script {
                                // SCAN_ID must be a positive integer (matches fetchCheckmarxReport's validation).
                                if (!("${SCAN_ID}" ==~ /^[1-9][0-9]*$/)) {
                                    error "scan_id '${SCAN_ID}' is invalid; expected a positive integer."
                                }
                                def token = sh(returnStdout: true, script: '''
                                    set +x
                                    curl --silent --show-error --fail \
                                        --request POST \
                                        --data-urlencode "username=${CX_USER}" \
                                        --data-urlencode "password=${CX_PASS}" \
                                        --data-urlencode "grant_type=password" \
                                        --data-urlencode "scope=sast_rest_api" \
                                        --data-urlencode "client_id=resource_owner_client" \
                                        --data-urlencode "client_secret=014DF517-39D1-4453-B7B3-9930C563627C" \
                                        "${CX_URL}/cxrestapi/auth/identity/connect/token" \
                                        | jq -r '.access_token'
                                ''').trim()
                                if (!token || token == 'null') {
                                    error "Failed to obtain Checkmarx access token."
                                }
                                env.CX_TOKEN = token

                                def reportId = sh(returnStdout: true, script: """
                                    set +x
                                    curl --silent --show-error --fail \
                                        --request POST \
                                        --header "Authorization: Bearer \${CX_TOKEN}" \
                                        --header "Content-Type: application/json" \
                                        --data '{"reportType": "XML", "scanId": ${SCAN_ID}}' \
                                        "\${CX_URL}/cxrestapi/reports/sastScan" \
                                        | jq -r '.reportId'
                                """).trim()

                                def status = 'InProcess'
                                for (int i = 0; i < 60; i++) {
                                    sleep time: 5, unit: 'SECONDS'
                                    status = sh(returnStdout: true, script: """
                                        set +x
                                        curl --silent --show-error --fail \
                                            --header "Authorization: Bearer \${CX_TOKEN}" \
                                            "\${CX_URL}/cxrestapi/reports/sastScan/${reportId}/status" \
                                            | jq -r '.status.value'
                                    """).trim()
                                    if (status == 'Created' || status == 'Failed') break
                                }
                                if (status != 'Created') {
                                    error "Checkmarx report status '${status}' (expected 'Created')."
                                }
                                sh """
                                    set +x
                                    curl --silent --show-error --fail \
                                        --header "Authorization: Bearer \${CX_TOKEN}" \
                                        --output checkmarx.xml \
                                        "\${CX_URL}/cxrestapi/reports/sastScan/${reportId}"
                                """
                            }
                        }
                    }
                }
            }
            stage('normalize findings') {
                steps {
                    dir('code-repo') {
                        sh '''
                            set -euo pipefail
                            gen_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
                            python3 .devsecops/scripts/collect-findings.py \
                                --generated-at "$gen_at" --out findings.json \
                                --inputs checkmarx:sast:checkmarx.xml
                        '''
                    }
                }
            }
            stage('agentic remediation') {
                steps {
                    dir('code-repo') {
                        // AWS credentials for Bedrock are expected in the agent environment.
                        sh """
                            set -euo pipefail
                            export AGENT_CMD='${AGENT_CMD}'
                            bash .devsecops/scripts/run-agent.sh triage findings.json --out agent-triage.json || true
                            bash .devsecops/scripts/run-agent.sh fix-all findings.json --out agent-fix-all.json || true
                        """
                    }
                }
            }
            stage('raise remediation PR') {
                steps {
                    dir('code-repo') {
                        withCredentials([usernamePassword(
                                credentialsId: 'github-credentials',
                                usernameVariable: 'GH_USER',
                                passwordVariable: 'GH_TOKEN'
                        )]) {
                            sh '''
                                set -euo pipefail
                                # Nothing changed -> no PR.
                                if git diff --quiet -- . ':(exclude).devsecops'; then
                                    echo "agent produced no file changes; no PR to raise"
                                    exit 0
                                fi
                                date_tag="$(date -u +%Y%m%d)"
                                branch="bot/code-fix-${date_tag}"
                                git config user.name "devsecops-bot"
                                git config user.email "devsecops-bot@users.noreply.github.com"
                                git checkout -B "$branch"
                                git add -- . ':(exclude).devsecops'
                                git commit -m "fix: remediate Checkmarx SAST findings"
                                # Derive owner/repo, then push with the token; never force.
                                repo_path="$(git config --get remote.origin.url | sed -E 's#.*github.com[/:]##; s#\\.git$##')"
                                auth_url="https://${GH_USER}:${GH_TOKEN}@github.com/${repo_path}.git"
                                git push "$auth_url" "HEAD:$branch"
                                summary="$(python3 .devsecops/scripts/summarize-remediation.py agent-fix-all.json || echo 'See changed files.')"
                                echo "$summary" > /tmp/pr-body.md
                                # Open the PR via the GitHub API (gh CLI if present, else curl).
                                if command -v gh >/dev/null 2>&1; then
                                    GH_TOKEN="$GH_TOKEN" gh pr create --repo "$repo_path" --base master --head "$branch" \
                                        --title "fix: remediate Checkmarx SAST findings (${date_tag})" \
                                        --body-file /tmp/pr-body.md || echo "PR may already exist"
                                else
                                    body="$(jq -Rs . < /tmp/pr-body.md)"
                                    curl --silent --show-error --fail \
                                        --header "Authorization: Bearer ${GH_TOKEN}" \
                                        --data "{\\"title\\":\\"fix: remediate Checkmarx SAST findings (${date_tag})\\",\\"head\\":\\"${branch}\\",\\"base\\":\\"master\\",\\"body\\":${body}}" \
                                        "https://api.github.com/repos/${repo_path}/pulls" || echo "PR may already exist"
                                fi
                            '''
                        }
                    }
                }
            }
        }
        post {
            unsuccessful {
                slackSend message: "[FAILURE] <${JOB_URL}|${JOB_NAME}>", color: '#FF0000'
            }
            success {
                script {
                    DOWNSTREAM_JOBS.each { value -> build(job: "${value}", wait: false) }
                }
            }
            always {
                cleanWs()
            }
        }
    }
}
