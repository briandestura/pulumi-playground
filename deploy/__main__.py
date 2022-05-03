import os
import pulumi as p
import pulumi_docker as docker
import pulumi_gcp as gcp


location = "australia-southeast1"

# Build API image:
api_image_name = "playground-sample-api"
api_image = docker.Image(
    api_image_name, 
    image_name=f"gcr.io/{gcp.config.project}/{api_image_name}/latest", 
    build=docker.DockerBuild(
        context="../api",
        extra_options=["--platform", "linux/amd64"]
    )
)

# Build Cloud Run Service:
api_service_name = "playground-sample-api"
api_service = gcp.cloudrun.Service(
    api_service_name,
    location=location,
    template=gcp.cloudrun.ServiceTemplateArgs(
        spec=gcp.cloudrun.ServiceTemplateSpecArgs(
            containers=[
                gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                    image=api_image.image_name,
                    ports=[
                        gcp.cloudrun.ServiceTemplateSpecContainerPortArgs(container_port=80)
                    ],
                    resources=gcp.cloudrun.ServiceTemplateSpecContainerResourcesArgs(
                        limits={
                            "memory": "256Mi",
                            "cpu": "1000m",
                        },
                        requests={
                            "memory": "64Mi",
                            "cpu": "200m",
                        },
                    )
                )
            ],
            container_concurrency=80
        ),
    ),
)

# Open the cloud run service for everyone:
iam_resource_name = "playground-sample-iam"
iam = gcp.cloudrun.IamMember(
    resource_name=iam_resource_name,
    service=api_service.name,
    location=location,
    role="roles/run.invoker",
    member="allUsers",
)

# Setup the static bucket
static_files_bucket_name = "playground-sample-static-bucket"
static_files_bucket = gcp.storage.Bucket(
    static_files_bucket_name,
    name=static_files_bucket_name,
    location=location,
    website=gcp.storage.BucketWebsiteArgs(
        main_page_suffix="index.html",
        not_found_page="404.html",
    ),
)

# Setup the public acl
acl_resource_name = "default-static-files-acl"
acl = gcp.storage.DefaultObjectAccessControl(
    acl_resource_name,
    bucket=static_files_bucket.name,
    role="READER",
    entity="allUsers",
)

# Add the static files
app_path = "../app"
for fname in os.listdir("../app"):
    if os.path.isfile(os.path.join(app_path, fname)):
        gcp.storage.BucketObject(
            fname,
            name=fname,
            bucket=static_files_bucket.name,
            source=p.asset.FileAsset(f'{app_path}/{fname}')
        )

p.export("cloud run url", api_service.statuses[0].url)
p.export("static files bucket url", p.output.Output.concat("http://storage.googleapis.com/", static_files_bucket.name, "/index.html"))