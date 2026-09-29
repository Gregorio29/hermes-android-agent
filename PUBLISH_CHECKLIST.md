# Pre-Publication Checklist — `hermes-android-agent`

- [x] Código revisado y modularizado (Python ADB/UIAutomator controller)
- [x] Secretos y credenciales revisados (0 hallazgos)
- [x] Discos virtuales AVD y APKs binarios pesados eliminados (~17 GB -> ~160 KB)
- [x] Volcados masivos de jerarquías XML eliminados
- [x] `.gitignore` creado con exclusiones de emuladores y APKs
- [x] `README.md` completo en inglés con ejemplos
- [x] `LICENSE` (MIT) integrado
- [x] `SECURITY.md` política de niveles operacionales (`SAFE`..`DESTRUCTIVE`)
- [x] Rutas dinamizadas con `ANDROID_HOME` y `HERMES_AVD_DIR`
- [x] Tests unitarios verificados y pasando (10 tests: 8 OK, 2 skipped)
- [x] Nombre de repositorio asignado: `hermes-android-agent`
- [x] Descripción y topics definidos
- [ ] Autenticación GitHub confirmada (`gh auth status`)
- [ ] Visibilidad configurada: `PUBLIC`
- [ ] Configuraciones de seguridad de GitHub (Dependabot, Secret Scanning)
- [ ] Commit inicial preparado
- [ ] Push remoto autorizado
