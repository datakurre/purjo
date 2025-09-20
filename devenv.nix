{
  pkgs,
  inputs,
  lib,
  ...
}:
{
  package.operaton.port = 8080;

  languages.python.interpreter = pkgs.python312;
  languages.python.workspaceRoot = ./.;
  languages.python.uv.package = lib.mkForce (
    pkgs.buildFHSEnv {
      name = "uv";
      targetPkgs = pkgs: [
        pkgs.python312
        inputs.uv2nix.packages.${pkgs.system}.uv-bin
      ];
      runScript = "uv";
    }
  );
  languages.python.pyprojectOverrides =
    final: prev:
    let
      packagesToBuildWithSetuptools = [
        "robotframework"
      ];
    in
    {
      "hatchling" = prev."hatchling".overrideAttrs (old: {
        propagatedBuildInputs = [ final."editables" ];
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

  packages = [
    pkgs.entr
    pkgs.findutils
    pkgs.git
    pkgs.gnumake
    pkgs.openssl
    pkgs.zip
  ];

  dotenv.disableHint = true;

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
