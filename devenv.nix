{ ... }:
let
  shell =
    {
      pkgs,
      config,
      inputs,
      lib,
      ...
    }:
    {
      package.image.path = "datakurre/purjo/purjo";
      package.image.package = config.outputs.python.app;
      package.image.callable = "pur";
      package.image.extraPackages = [
        pkgs.uv
        pkgs.python311
        pkgs.python312
        pkgs.python313
        pkgs.python314
      ];

      services.operaton.port = 8080;
      services.operaton.postgresql.enable = true;

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

      languages.python.interpreter = pkgs.python313;
      languages.python.workspaceRoot = ./.;
      languages.python.uv.package = lib.mkForce (
        pkgs.buildFHSEnv {
          name = "uv";
          targetPkgs = pkgs: [
            pkgs.python313
            inputs.uv2nix.packages.${pkgs.system}.uv-bin
          ];
          runScript = "uv";
        }
      );
      languages.python.pyprojectOverrides =
        final: prev:
        let
          packagesToBuildWithSetuptools = [
            "aiohttp"
            "coverage"
            "cmarkgfm"
            "markupsafe"
            "robotframework"
          ];
        in
        {
          "hatchling" = prev."hatchling".overrideAttrs (old: {
            propagatedBuildInputs = [ final."editables" ];
          });
          "pydantic-core" = prev."pydantic-core".overrideAttrs (old: {
            nativeBuildInputs =
              old.nativeBuildInputs
              ++ final.resolveBuildSystem ({
                "maturin" = [ ];
              });
          });
        }
        // builtins.listToAttrs (
          map (pkg: {
            name = pkg;
            value = prev.${pkg}.overrideAttrs (old: {
              nativeBuildInputs =
                old.nativeBuildInputs
                ++ final.resolveBuildSystem ({
                  "setuptools" = [ ];
                });
            });
          }) packagesToBuildWithSetuptools
        );

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
