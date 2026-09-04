{ ... }:
let
  shell =
    {
      pkgs,
      config,
      devenv-module-operaton,
      ...
    }:
    {
      services.operaton.port = 8080;
      services.operaton.package =
        devenv-module-operaton.packages.${pkgs.stdenv.hostPlatform.system}.default;
      services.operaton.postgres.enable = true;

      services.vault = {
        enable = true;
        disableMlock = true;
        ui = true;
      };

      processes.vault-configure-kv.exec =
        let
          configureScript = pkgs.writeShellScriptBin "configure-vault-kv" ''
            set -euo pipefail

            # Wait for the vault server to start up
            response=""
            while [ -z "$response" ]; do
              response=$(${pkgs.curl}/bin/curl -s --max-time 5 "${config.env.VAULT_API_ADDR}/v1/sys/init" | ${pkgs.jq}/bin/jq '.initialized' || true)
              if [ -z "$response" ]; then
                echo "Waiting for vault server to respond..."
                sleep 1
              fi
            done
            while [ ! -f "${config.env.DEVENV_STATE}/env_file" ]; do
                sleep 1s
            done

            # Export VAULT_TOKEN
            source ${config.env.DEVENV_STATE}/env_file

            # Ensure /kv/secret
            if ! ${pkgs.vault-bin}/bin/vault secrets list | grep -q '^secret/'; then
              ${pkgs.vault-bin}/bin/vault secrets enable -path=secret kv-v2
            fi
          '';
        in
        "${configureScript}/bin/configure-vault-kv";

      languages.python.enable = true;
      languages.python.version = "3.13";
      languages.python.uv.enable = true;
      languages.python.uv.sync.enable = true;
      languages.python.venv.enable = true;

      outputs.python.app = config.languages.python.import ./. { };

      packages =
        let
          mockoon-cli = pkgs.callPackage ./fixture/mockoon { };
        in
        [
          pkgs.entr
          pkgs.findutils
          pkgs.mockoon
          pkgs.git
          pkgs.gnumake
          pkgs.openssl
          pkgs.vim
          pkgs.zip
          pkgs.curl
          pkgs.jq
          pkgs.vault-bin
          pkgs.nixfmt-rfc-style
          mockoon-cli
        ];

      dotenv.enable = true;

      enterShell = ''
        # Export VAULT_TOKEN
        if [ -f "${config.env.DEVENV_STATE}/env_file" ]; then
          source ${config.env.DEVENV_STATE}/env_file
        fi
        export UV_NO_CONFIG=1
        export UV_NO_WORKSPACE=1
      '';

      enterTest = ''
        wait_for_port 8080 60
        wait_for_port 8200 60
        source ${config.env.DEVENV_STATE}/env_file
      '';

      processes.mockoon.exec = "mockoon-cli start --data ./fixture/mockoon/data.json --port 3080 --hostname 0.0.0.0 --log-transaction";

      cachix.pull = [ "datakurre" ];
    };
  devcontainer =
    { ... }:
    {
      devcontainer.enable = true;
    };
in
{
  profiles.shell.module = {
    imports = [ shell ];
  };
  profiles.devcontainer.module = {
    imports = [ devcontainer ];
  };
}
