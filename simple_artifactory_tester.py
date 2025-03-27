import os
import json
import subprocess
import requests
from pathlib import Path

class SimpleArtifactoryTester:
    def __init__(self, artifactory_url, username, password):
        self.artifactory_url = artifactory_url.rstrip('/')
        self.auth = (username, password)
        self.test_dir = Path("test_images")
        self.test_dir.mkdir(exist_ok=True)

    def run_docker_command(self, command):
        """Run a docker command and return its output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running docker command: {e.stderr}")
            return None

    def list_images(self, repo_path):
        """List all Docker images in the specified Artifactory repository."""
        api_url = f"{self.artifactory_url}/api/docker/{repo_path}/v2/_catalog"
        response = requests.get(api_url, auth=self.auth)
        if response.status_code == 200:
            return response.json().get('repositories', [])
        else:
            print(f"Error listing images: {response.status_code}")
            return []

    def get_image_tags(self, repo_path, image_name):
        """Get all tags for a specific image."""
        api_url = f"{self.artifactory_url}/api/docker/{repo_path}/v2/{image_name}/tags/list"
        response = requests.get(api_url, auth=self.auth)
        if response.status_code == 200:
            return response.json().get('tags', [])
        else:
            print(f"Error getting tags for {image_name}: {response.status_code}")
            return []

    def create_dockerfile(self, image_name, tag):
        """Create a Dockerfile for testing the specified image."""
        dockerfile_path = self.test_dir / f"Dockerfile.{image_name.replace('/', '_')}_{tag}"
        with open(dockerfile_path, 'w') as f:
            f.write(f"FROM {image_name}:{tag}\n")
            f.write("CMD [\"sh\", \"-c\", \"echo 'Image test successful' && exit 0\"]")
        return dockerfile_path

    def build_and_run(self, dockerfile_path, image_name, tag):
        """Build and run the Docker image using docker CLI commands."""
        try:
            # Build the image
            build_tag = f"test_{image_name.replace('/', '_')}_{tag}"
            build_cmd = f"docker build -t {build_tag} -f {dockerfile_path} {dockerfile_path.parent}"
            if not self.run_docker_command(build_cmd):
                return False

            # Run the container
            run_cmd = f"docker run --rm {build_tag}"
            output = self.run_docker_command(run_cmd)
            if output:
                print(f"Container logs for {image_name}:{tag}:\n{output}")
                return True
            return False

        except Exception as e:
            print(f"Error testing {image_name}:{tag}: {str(e)}")
            return False

    def test_images(self, repo_path):
        """Test all images in the specified repository."""
        images = self.list_images(repo_path)
        for image_name in images:
            tags = self.get_image_tags(repo_path, image_name)
            for tag in tags:
                print(f"\nTesting {image_name}:{tag}")
                dockerfile_path = self.create_dockerfile(image_name, tag)
                success = self.build_and_run(dockerfile_path, image_name, tag)
                print(f"Test {'successful' if success else 'failed'} for {image_name}:{tag}")

def main():
    # Get Artifactory credentials from environment variables
    artifactory_url = os.getenv('ARTIFACTORY_URL')
    username = os.getenv('ARTIFACTORY_USERNAME')
    password = os.getenv('ARTIFACTORY_PASSWORD')
    repo_path = os.getenv('ARTIFACTORY_REPO_PATH', 'docker-local')
    
    if not all([artifactory_url, username, password]):
        print("Please set ARTIFACTORY_URL, ARTIFACTORY_USERNAME, and ARTIFACTORY_PASSWORD environment variables")
        return
    
    tester = SimpleArtifactoryTester(artifactory_url, username, password)
    tester.test_images(repo_path)

if __name__ == "__main__":
    main() 
