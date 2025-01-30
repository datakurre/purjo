{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:
{
  imports = [
    ./devenv/modules/operaton.nix
    ./devenv/modules/python.nix
  ];

  package.operaton.path = ./fixture;

  languages.python.interpreter = pkgs.python312;
  languages.python.pyprojectOverrides = final: prev: { };

  packages = [
    pkgs.entr
    pkgs.findutils
    pkgs.git
    pkgs.gnumake
    pkgs.openssl
    pkgs.zip
  ];

  dotenv.disableHint = true;

  enterShell = ''
    unset PYTHONPATH
    export UV_NO_SYNC=1
    export UV_PYTHON_DOWNLOADS=never
    export REPO_ROOT=$(git rev-parse --show-toplevel)
  '';

  # processes.runner.exec = "make -s watch";

  enterTest = ''
    wait_for_port 8080 60
  '';

  cachix.pull = [ "datakurre" ];

  devcontainer.enable = true;

  git-hooks.hooks.treefmt = {
    enable = true;
    settings.formatters = [
      pkgs.nixfmt-rfc-style
    ];
  };
}
