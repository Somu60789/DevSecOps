// Example job definition. Loads your Jenkins shared library that exposes the
// remediateCheckmarx step, then calls it. SCAN_ID comes from a prior scan or a
// fetch-report step.
//
// To make the step available, publish jenkins/vars/ from this product as a
// Jenkins Global Pipeline Library, or vendor it into your existing library.

library identifier: 'devsecops@v1', changelog: false, retriever: modernSCM(github(
    credentialsId: 'github-credentials', repository: 'devsecops', repoOwner: 'your-org'
))

properties([
    parameters([
        string(name: 'SCAN_ID', defaultValue: '', description: 'Checkmarx scan id to remediate'),
        string(name: 'CODE_REPO', defaultValue: 'https://github.com/your-org/your-service.git',
               description: 'Code repository to remediate and raise the PR against'),
        string(name: 'CHECKMARX_URL', defaultValue: 'https://checkmarx.your-company.example',
               description: 'On-prem CxSAST server URL')
    ])
])

remediateCheckmarx {
    code_repo      = params.CODE_REPO
    scan_id        = params.SCAN_ID
    checkmarx_url  = params.CHECKMARX_URL
    devsecops_repo = 'https://github.com/your-org/devsecops.git'
    devsecops_ref  = 'v1'
    agent_cmd      = 'python3 .devsecops/scripts/agents/bedrock-agent.py'
}
