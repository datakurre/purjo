{
  description = "purjo";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
    flake-utils-vasara.url = "gitlab:vasara-bpm/flake-utils-vasara";
    flake-utils-vasara.inputs.nixpkgs.follows = "nixpkgs";
  };
  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      flake-utils-vasara,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        packagesToBuildWithSetuptools = [
          "aiohttp"
          "coverage"
          "cmarkgfm"
          "markupsafe"
          "robotframework"
        ];
        pythonApp = flake-utils-vasara.lib.mkPythonApp {
          inherit pkgs;
          python = pkgs.python313;
          workspaceRoot = ./.;
          overrides =
            final: prev:
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
        };
      in
      {
        packages.default = pythonApp.package;
        packages.image = flake-utils-vasara.lib.mkContainerImage {
          inherit pkgs;
          path = "datakurre/purjo/purjo";
          package = pythonApp.package;
          callable = "pur";
          labels = ./Labels.json;
          extraPackages = [
            pkgs.uv
            pkgs.python311
            pkgs.python312
            pkgs.python313
            pkgs.python314
          ];
        };

        packages.container = self.packages.${system}.image;
      }
    );
}
