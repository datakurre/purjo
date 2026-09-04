let
  shell =
    {
      pkgs,
      lib,
      config,
      devenv-module-operaton,
      ...
    }:
    {
      services.operaton = {
        enable = true;
        port = 8080;
        forwardHeadersStrategy = "native";
        package = devenv-module-operaton.packages.${pkgs.stdenv.hostPlatform.system}.default;
        deployment = ./fixture/operaton;
        oauth2 = {
          enable = true;
          issuerUri = "http://localhost:8081/realms/operaton";
        };
        postgres.enable = true;
      };

      services.keycloak = {
        enable = true;
        settings.http-port = 8081;
        realms.operaton = {
          path = "./fixture/keycloak/operaton-realm.json";
          import = true;
          export = true;
        };
      };

      services.vault = {
        enable = true;
        disableMlock = true;
        ui = true;
      };

      processes.vault-configure-kv.exec =
        let
          configureScript = pkgs.writeShellScriptBin "configure-vault-kv" ''
            set -euo pipefail

            # Both waits below are bounded. `devenv test` does not run
            # enterTest until every process is ready, so an unbounded wait
            # here does not just stall this one process, it hangs the entire
            # run: CI sat for 26 minutes with this script's `sleep` as the
            # only thing still moving, and would have burned the full 6 hour
            # job timeout. Failing loudly names the missing precondition
            # instead.
            timeout_seconds=120

            # Wait for the vault server to start up
            response=""
            deadline=$((SECONDS + timeout_seconds))
            while [ -z "$response" ]; do
              if [ "$SECONDS" -ge "$deadline" ]; then
                echo "configure-vault-kv: vault did not respond at ${config.env.VAULT_API_ADDR} within $timeout_seconds seconds" >&2
                exit 1
              fi
              response=$(${pkgs.curl}/bin/curl -s --max-time 5 "${config.env.VAULT_API_ADDR}/v1/sys/init" | ${pkgs.jq}/bin/jq '.initialized' || true)
              if [ -z "$response" ]; then
                echo "Waiting for vault server to respond..."
                sleep 1
              fi
            done

            # Wait for vault-configure to write the root token
            deadline=$((SECONDS + timeout_seconds))
            while [ ! -f "${config.env.DEVENV_STATE}/env_file" ]; do
              if [ "$SECONDS" -ge "$deadline" ]; then
                echo "configure-vault-kv: vault-configure did not write ${config.env.DEVENV_STATE}/env_file within $timeout_seconds seconds" >&2
                exit 1
              fi
              sleep 1
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

      # devenv's own `vault-configure` deliberately never exits -- its script
      # ends in `while true; do sleep 1; done` after unsealing -- and it ships
      # no readiness probe, so it sits in Running/not-ready forever. devenv's
      # own shell-side waiter skips such processes explicitly ("Filter
      # not_ready processes that have readiness probes"), but `devenv test`
      # waited on it: CI reached this point and then produced no further
      # output for 26 minutes, with `configure-vault` and its `sleep` still
      # alive at cancellation and no make/pytest process ever spawned.
      #
      # Give it the probe it lacks: env_file is what it writes once vault is
      # initialised, and what enterTest sources straight afterwards.
      processes.vault-configure.ready = {
        exec = "test -f ${config.env.DEVENV_STATE}/env_file";
        initial_delay = 1;
        period = 1;
      };

      languages.python.enable = true;
      languages.python.version = "3.13";
      languages.python.uv.enable = true;
      languages.python.uv.sync = {
        enable = true;
        allGroups = true;
      };
      languages.python.venv.enable = true;

      outputs.python.app = config.languages.python.import ./. { };

      # https://devenv.sh/pre-commit-hooks/
      # Keeps `treefmt` runnable as a plain command (via `make format` /
      # `devenv test`) without installing it as an actual git hook: the
      # installer only skips installing a hook type when every hook enabled
      # for it has stages = [ "manual" ], so it must be set on the hook
      # itself and not only as default_stages, which does not affect that
      # decision.
      git-hooks.hooks.treefmt = {
        enable = true;
        stages = [ "manual" ];
        settings.formatters = [ pkgs.nixfmt-rfc-style ];
      };
      # devenv's own `devenv:git-hooks:run` task (run by `devenv test`) always
      # does a plain `prek run -a`, which filters to the `pre-commit` stage
      # regardless of the hooks' configured stage. Since every hook here is
      # `manual`-only (see above), that leaves nothing to run and `devenv
      # test` fails outright with "No hooks found for stage `pre-commit`".
      # Override it to run the `manual` stage instead, mirroring what
      # git-hooks.nix's own check derivation does for this same setup.
      tasks."devenv:git-hooks:run".exec = lib.mkForce ''
        export PATH="${config.env.UV_PROJECT_ENVIRONMENT}/bin:$PATH"
        ${lib.getExe config.git-hooks.package} run -c ${config.git-hooks.configPath} --hook-stage manual --all-files
      '';

      packages =
        let
          mockoon-cli = pkgs.callPackage ./fixture/mockoon { };
        in
        [
          pkgs.entr
          pkgs.findutils
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
      '';

      enterTest = ''
        wait_for_port 8080 60
        wait_for_port 8200 60
        wait_for_port 8081 60
        source ${config.env.DEVENV_STATE}/env_file
        make test
        make test-e2e
      '';

      processes.mockoon.exec = "mockoon-cli start --data ./fixture/mockoon/data.json --port 3080 --hostname 0.0.0.0 --log-transaction";

      # "nixpkgs-python" serves the prebuilt interpreter for
      # `languages.python.version` above; without it that is a source build.
      # It only resolves as long as devenv.yaml leaves the nixpkgs-python
      # input's own nixpkgs pin alone -- see the comment there.
      cachix.pull = [
        "datakurre"
        "nixpkgs-python"
      ];
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
