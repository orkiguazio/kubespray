@Library('pipelinex@development') _

def config = common.get_config()

def props = [
    buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '30', numToKeepStr: '1000')),
    disableConcurrentBuilds()
]

if (config.cron.get(env.BRANCH_NAME)) {
    props.add(pipelineTriggers([cron(config.cron.get(env.BRANCH_NAME))]))
}

properties(props)


timestamps {
common.notify_slack {
node('centos76') {

    stage('git clone') {
        deleteDir()
        def scm_vars = checkout scm
        env.kubespray_hash = scm_vars.GIT_COMMIT
        currentBuild.description = "hash = ${env.kubespray_hash}"
    }

    def img_name = "kubespray:${env.kubespray_hash}"
    def image = stage('build') {
        withCredentials([string(credentialsId: 'sudo_password', variable: 'sudo_password')]) {
            common.shell(['./prepare_offline_version.sh', env.sudo_password])
        }

        return docker.build(img_name, '--file igz_Dockerfile .')
    }

    def rel_dir = "build_by_hash/kubespray/${env.kubespray_hash}/pkg/kubespray"
    def nas_dir = "/mnt/nas/${rel_dir}"
    def output_name = 'kubespray.tar.xz'
    def nas_image = "${nas_dir}/${output_name}"
    stage('save to nas') {
        try {
            common.shell(['mkdir', '-p', nas_dir])
            sh("docker save ${img_name} | xz -9 > ${nas_image}")
        } finally {
            common.shell(['docker', 'rmi', image.id])
        }
    }

    stage('upload to s3') {
        def bucket = 'iguazio-versions-eu'
        def bucket_region = 'eu-central-1'
        common.upload_to_s3(bucket, bucket_region, nas_image, "${rel_dir}/${output_name}")
    }
}}}
