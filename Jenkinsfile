pipeline {
    agent {
        label 'cambuilder'
    }

    stages {
        stage('Checkout SCM') {
            steps{
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "refs/heads/${env.BRANCH_NAME}"]],
                    extensions: [[$class: 'LocalBranch']],
                    userRemoteConfigs: scm.userRemoteConfigs,
                    doGenerateSubmoduleConfigurations: false,
                    submoduleCfg: []
                ])
            }
        }

        stage ('Static analysis') {
            steps {
                sh 'pylint ./astrokat --output-format=parseable --exit-zero > pylint.out'
            }
            post {
                always {
                    recordIssues(tool: pyLint(pattern: 'pylint.out'))
                }
            }
        }

        stage('Install & Unit Tests') {
            options {
                timestamps()
                timeout(time: 30, unit: 'MINUTES') 
            }
            steps
                {
                        sh 'pip install . -U --pre --user'
                        sh 'python setup.py nosetests --with-xunit --with-xcoverage --xcoverage-file=coverage.xml --cover-package=astrokat --cover-inclusive'
                } 
                
                post {
                    always {
                        junit 'nosetests.xml'
                        cobertura coberturaReportFile: 'coverage.xml'
                        archiveArtifacts '*.xml'
                    }
                }
            }

        stage('Build .whl & .deb') {
            steps {
                sh 'fpm -s python -t deb .'
                sh 'python setup.py bdist_wheel'
                sh 'mv *.deb dist/'
            }
        }

        stage('Archive build artifact: .whl & .deb'){
            steps {
                archiveArtifacts 'dist/*'
            }
        }

        stage('Trigger downstream publish') {
            when {
                branch 'master'
            }
            steps {
                build job: 'ci.publish-artifacts', parameters: [
                    string(name: 'job_name', value: "${env.JOB_NAME}"),
                    string(name: 'build_number', value: "${env.BUILD_NUMBER}")]
            }
        }
    }
}
