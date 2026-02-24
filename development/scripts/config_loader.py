"""
Config Loader for Vulcan Brownout

Loads YAML configuration from an environment directory.
By default uses development/environments/{env}/ but supports a custom
env_base_dir for environments stored elsewhere (e.g. quality/environments/).
Merges main config with secrets from vulcan-brownout-secrets.yaml.

Usage:
    # Default (development/environments/docker/)
    config = ConfigLoader('docker').load()
    print(config['ha']['token'])

    # Custom base dir (quality/environments/staging/)
    config = ConfigLoader('staging', env_base_dir='quality/environments').load()
    print(config['ha']['token'])
"""

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML is required. Install with: pip install pyyaml",
        flush=True
    )
    raise

from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """Load and merge YAML configuration files for an environment."""

    def __init__(self, environment: str, env_base_dir: Optional[str] = None):
        """
        Initialize config loader for an environment.

        Args:
            environment: Environment name (e.g. 'docker', 'staging')
            env_base_dir: Optional path relative to repo root for the
                environments base directory. Defaults to
                'development/environments'. Use 'quality/environments'
                for staging configs stored under quality/.
        """
        self.environment = environment
        self.repo_root = self._find_repo_root()

        if env_base_dir is not None:
            self.env_dir = self.repo_root / env_base_dir / environment
        else:
            self.env_dir = self.repo_root / 'development' / 'environments' / environment

        if not self.env_dir.exists():
            raise ValueError(f"Environment directory not found: {self.env_dir}")

    def load(self) -> Dict[str, Any]:
        """
        Load and merge configuration files.

        Returns:
            Merged configuration dictionary

        Raises:
            FileNotFoundError: If main config file is missing
        """
        config_file = self.env_dir / 'vulcan-brownout-config.yaml'
        secrets_file = self.env_dir / 'vulcan-brownout-secrets.yaml'

        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}"
            )

        # Load main config
        config = self._load_yaml(config_file)

        # Load and merge secrets if available
        if secrets_file.exists():
            secrets = self._load_yaml(secrets_file)
            config = self._deep_merge(config, secrets)
        else:
            print(
                f"Warning: Secrets file not found: {secrets_file}\n"
                f"Run: cp {secrets_file}.example {secrets_file}",
                flush=True
            )

        return config

    def get_env_vars(self) -> Dict[str, str]:
        """
        Load configuration and convert to environment variables.

        Returns:
            Dictionary of environment variable names to values
        """
        config = self.load()
        env_vars = {}

        # Flatten config to environment variables
        # Combine HA_URL and HA_PORT into single HA_URL
        ha_url = config.get('ha', {}).get('url', '')
        ha_port = config.get('ha', {}).get('port', '')
        if ha_url and ha_port:
            env_vars['HA_URL'] = f"{ha_url}:{ha_port}"
        elif ha_url:
            env_vars['HA_URL'] = ha_url
        else:
            env_vars['HA_URL'] = ''

        env_vars['HA_USERNAME'] = config.get('ha', {}).get('username', '')
        env_vars['HA_PASSWORD'] = config.get('ha', {}).get('password', '')
        env_vars['HA_TOKEN'] = config.get('ha', {}).get('token', '')

        env_vars['SSH_HOST'] = config.get('ssh', {}).get('host', '')
        env_vars['SSH_PORT'] = str(config.get('ssh', {}).get('port', ''))
        env_vars['SSH_USER'] = config.get('ssh', {}).get('user', '')
        key_file = config.get('ssh', {}).get('key_file', '')
        env_vars['SSH_KEY_PATH'] = str(self.env_dir / key_file) if key_file else ''
        env_vars['HA_CONFIG_PATH'] = config.get('ssh', {}).get(
            'ha_config_path', ''
        )

        return env_vars

    @staticmethod
    def _load_yaml(file_path: Path) -> Dict[str, Any]:
        """Load a YAML file safely."""
        with open(file_path, 'r') as f:
            content = yaml.safe_load(f)
            return content if content else {}

    @staticmethod
    def _deep_merge(
        base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively merge override dict into base dict.

        Args:
            base: Base configuration dictionary
            override: Configuration to merge in

        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(
                value, dict
            ):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _find_repo_root() -> Path:
        """Find the repository root directory by looking for .git."""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / '.git').exists():
                return parent
        raise RuntimeError(
            "Could not find repository root. Make sure .git exists."
        )


if __name__ == '__main__':
    import sys
    import json

    # Command-line usage: python config_loader.py <environment>
    if len(sys.argv) < 2:
        print("Usage: python config_loader.py <environment>")
        print("  environment: docker or staging")
        sys.exit(1)

    env = sys.argv[1]
    try:
        loader = ConfigLoader(env)
        config = loader.load()
        print(json.dumps(config, indent=2))
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
