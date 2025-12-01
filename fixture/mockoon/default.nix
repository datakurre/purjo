{
  pkgs ? import <nixpkgs> { },
}:

pkgs.buildNpmPackage {
  pname = "mockoon-cli";
  version = (builtins.fromJSON (builtins.readFile ./package.json)).version;

  src = ./.;

  npmDepsHash = "sha256-DKA6i32fP76dFQlbmgqqb3wjZ2achQbpD4zCUjRjZiI=";
  makeCacheWritable = true;
  dontNpmBuild = true;

  nativeBuildInputs = [ pkgs.makeWrapper ];

  installPhase = ''
    runHook preInstall
    mkdir -p $out/lib
    cp -r node_modules $out/lib/
    makeWrapper ${pkgs.nodejs}/bin/node $out/bin/mockoon-cli \
      --set NODE_PATH "$out/lib/node_modules" \
      --add-flags "$out/lib/node_modules/@mockoon/cli/bin/run"
    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Mockoon CLI";
    homepage = "https://mockoon.com";
    license = licenses.isc;
  };
}
