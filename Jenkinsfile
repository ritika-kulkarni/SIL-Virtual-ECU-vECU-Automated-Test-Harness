pipeline {
  agent {
    dockerfile {
      filename 'docker/Dockerfile.ci'
      dir '.'
      args '-u root:root'
    }
  }

  options {
    timestamps()
    timeout(time: 45, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    BUILD_ID = "${env.BUILD_NUMBER}"
    BRANCH_NAME = "${env.CHANGE_BRANCH ?: env.BRANCH_NAME ?: 'local'}"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install harness') {
      steps {
        sh 'python3 -m pip install -e ".[dev]"'
      }
    }

    stage('Unit tests (Python)') {
      steps {
        sh 'pytest tests/unit -q --cov=sil_harness --cov-report=term-missing'
      }
    }

    stage('Build vECU + GTest') {
      steps {
        sh '''
          if command -v ninja >/dev/null 2>&1; then
            cmake -S vecu -B vecu/build -G Ninja -DCOVERAGE=ON -DBUILD_TESTS=ON
          else
            cmake -S vecu -B vecu/build -DCOVERAGE=ON -DBUILD_TESTS=ON
          fi
          cmake --build vecu/build -j
          ./vecu/build/vecu_tests
        '''
      }
    }

    stage('SIL scenarios') {
      steps {
        sh 'sil-harness run --config config/harness.yaml --scenarios all --skip-build'
      }
    }

    stage('Coverage HTML') {
      steps {
        sh 'bash scripts/generate_coverage.sh'
      }
    }

    stage('Publish Artifactory') {
      steps {
        script {
          // Prefer mock publisher from harness.yaml; inject HTTP credentials when configured.
          if (fileExists('config/harness.yaml') && readFile('config/harness.yaml').contains('mode: http')) {
            withCredentials([
              usernamePassword(
                credentialsId: 'artifactory-sil',
                usernameVariable: 'ARTIFACTORY_USER',
                passwordVariable: 'ARTIFACTORY_PASSWORD'
              )
            ]) {
              sh 'sil-harness publish --config config/harness.yaml --branch "$BRANCH_NAME"'
            }
          } else {
            sh 'sil-harness publish --config config/harness.yaml --branch "$BRANCH_NAME"'
          }
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true
      publishHTML(target: [
        allowMissing: true,
        alwaysLinkToLastBuild: true,
        keepAll: true,
        reportDir: 'artifacts/reports',
        reportFiles: 'sil_report.html',
        reportName: 'SIL Report'
      ])
    }
  }
}
