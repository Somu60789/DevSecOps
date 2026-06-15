// Example job definition (place under ci/scans/... in ep-pipelines, alongside
// the existing fetch-checkmarx-report job). Loads the shared library, then calls
// the agentic remediation step. SCAN_ID comes from a prior scan or the
// fetch-checkmarx-report output.

library identifier: 'ep-pipelines@master', changelog: false, retriever: modernSCM(github(
    credentialsId: 'github-credentials', repository: 'ep-pipelines', repoOwner: 'tmlconnected'
))

properties([
    parameters([
        string(name: 'SCAN_ID', defaultValue: '', description: 'Checkmarx scan id to remediate'),
        string(name: 'CODE_REPO', defaultValue: 'https://github.com/tmlconnected/cvp-vehicle-service.git',
               description: 'Code repository to remediate and raise the PR against')
    ])
])

remediateCheckmarx {
    code_repo      = params.CODE_REPO
    scan_id        = params.SCAN_ID
    devsecops_repo = 'https://github.com/Somu60789/DevSecOps.git'
    devsecops_ref  = 'v1'
    agent_cmd      = 'python3 .devsecops/scripts/agents/bedrock-agent.py'
}
