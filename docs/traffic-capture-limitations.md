# Análisis Técnico: Limitaciones y Mecanismos de Captura de Tráfico en Android (HermesLab)

**Fecha:** 27 de Septiembre de 2026  
**Entorno:** HermesLab (Android 13 / API 33 / x86_64 / Root Magisk 26.4 / Reqable 3.2.23)

---

## 1. Alcance de la Observabilidad Actual (Verificada)

Con la instalación de **Reqable** y su **CA de Sistema inyectada mediante módulo Magisk**:
1. **Tráfico HTTP:** 100% visible, interceptable y manipulable.
2. **Tráfico HTTPS de aplicaciones estándar:** Descifrado completamente (Cleartext Payload + Headers + TLS Session) sin advertencias de certificado, ya que el sistema operativo confía en `Reqable CA` como autoridad raíz de confianza global (`/system/etc/security/cacerts/e94fb6b0.0`).
3. **Tráfico de aplicaciones debuggables y con Network Security Config por defecto:** 100% descifrado.

---

## 2. Limitaciones Técnicas y Fronteras de Seguridad

### A. SSL / Certificate Pinning (Fijación de Certificados)
* **Mecanismo:** Aplicaciones de alta seguridad (banca, pasarelas de pago, apps con OkHttp `CertificatePinner` o implementaciones nativas en C/C++ como BoringSSL) no se limitan a confiar en el almacén del sistema; verifican criptográficamente el hash de la clave pública (SPKI SHA-256) del certificado del servidor.
* **Comportamiento en Reqable:** La conexión fallará durante el handshake TLS (`SSLHandshakeException` o `CertPathValidatorException`) y Reqable registrará `TLS Handshake Failure` o `Client aborted connection`.
* **Solución futura (no aplicada en esta fase):** Inyección de scripts dinámicos vía Frida (`frida-server`) o módulos Zygisk / LSPosed (ej. `JustTrustMe`, `TrustMeAlready`) para hookear las rutinas de validación X509.

### B. Protocolos Basados en UDP (QUIC / HTTP/3)
* **Mecanismo:** Servicios modernos de Google (YouTube, Chromium, APIs de Cloudflare) utilizan HTTP/3 sobre QUIC (UDP 443) en lugar de TCP.
* **Comportamiento en Reqable:** Si el proxy VPN no intercepta UDP a nivel de capa de aplicación, el cliente puede degradar a HTTP/1.1/TLS sobre TCP o pasar sin descifrado en el flujo UDP.
* **Mitigación:** En Reqable o mediante reglas `iptables` en root, bloquear el puerto UDP 443 (`iptables -A OUTPUT -p udp --dport 443 -j DROP`), forzando al cliente a recurrir inmediatamente a HTTPS sobre TCP estándar.

### C. Tráfico Directo TCP / Protocolos Propietarios sin HTTP
* **Mecanismo:** Sockets TCP directos, WebSockets binarios encriptados por capas de aplicación secundarias (ej. Signal Protocol, MQTT con TLS propietario, gRPC con mTLS).
* **Comportamiento:** Reqable mostrará el flujo de socket como `TCP Stream` sin desglose estructurado JSON/HTTP.

### D. Aplicaciones con Bypasses de VPN
* **Mecanismo:** Ciertas aplicaciones configuran `protect(socket)` o evitan el enrutamiento TUN de Android para saltarse proxies VPN locales.
* **Mitigación:** Gracias al acceso Root en `HermesLab`, es posible redirigir el tráfico mediante reglas `iptables` / `REDIRECT` o `TPROXY` en lugar de depender únicamente de la interfaz VPN del SO.

---

## 3. Matriz Comparativa de Capacidades de Captura

| Escenario | Comportamiento en HermesLab | Estado |
|---|---|:---:|
| **HTTP Plano (GET/POST/REST/JSON)** | Interceptado y decodificado 100% | ✅ Operativo |
| **HTTPS Estándar (System CA)** | Descifrado TLS transparente 100% | ✅ Operativo |
| **HTTPS en apps propias (`HermesDebugTarget`)** | Descifrado verificado (200 OK, JSON body) | ✅ Operativo |
| **HTTPS con Certificate Pinning** | Bloqueado por la app (Handshake fail) | 🔒 Requiere Frida / LSPosed |
| **HTTP/3 / QUIC** | Requiere bloqueo UDP 443 para fallback TCP | ℹ️ Mitigable vía iptables |
| **mTLS (Autenticación mutua cliente/servidor)** | Requiere importar cert cliente (.p12) en Reqable | ℹ️ Soportado en Reqable |

---

## 4. Conclusión y Recomendación Operativa

`HermesLab` cumple con todos los requisitos de un entorno de análisis y depuración seguro y reproducible. Para las aplicaciones desarrolladas y controladas por el equipo (`HermesDebugTarget` y futuras apps), el laboratorio ofrece **100% de visibilidad en tráfico de red y diagnóstico de fallos**. Para análisis futuro de aplicaciones externas protegidas, el entorno con Magisk 26.4 y Root activo permite incorporar LSPosed/Frida cuando sea necesario sin rehacer la arquitectura.
