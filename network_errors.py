"""Safe network diagnostics without response bodies, URLs or credentials."""
import socket
import ssl
import urllib.error


def explain(error):
    reason=error.reason if isinstance(error,urllib.error.URLError) else error
    if isinstance(reason,ssl.SSLCertVerificationError):
        return ('TLS_CERTIFICATE: Python не смог проверить сертификат сервера. Проверьте дату и время Windows. '
                'Если используется антивирусная HTTPS-проверка или корпоративный прокси, нужен его доверенный сертификат в Windows/Python. Проверка сертификатов не отключена.')
    if isinstance(reason,ssl.SSLError):
        known={'UNEXPECTED_EOF_WHILE_READING':'соединение закрыто до завершения TLS', 'WRONG_VERSION_NUMBER':'получен ответ, не соответствующий ожидаемому TLS; проверьте тип прокси', 'TLSV1_ALERT_PROTOCOL_VERSION':'сервер или посредник отклонил версию TLS', 'SSLV3_ALERT_HANDSHAKE_FAILURE':'сервер или посредник отклонил согласование TLS', 'TLSV1_ALERT_INTERNAL_ERROR':'сервер или посредник сообщил внутреннюю ошибку TLS'}
        code=getattr(reason,'reason',None)
        detail=(' ['+code+']: '+known[code]) if code in known else ''
        return 'TLS_HANDSHAKE'+detail+': не удалось установить защищённое соединение. Причину нужно проверить сравнением Python и Windows curl; ключ ещё не проверен.'
    if isinstance(reason,socket.gaierror):
        return 'DNS: не удалось определить адрес сервера. Проверьте домен в базовом URL и доступность сайта; VPN только в браузере не обеспечивает доступ для Python.'
    if isinstance(reason,(TimeoutError,socket.timeout)):
        return 'TIMEOUT: сервер или сетевой посредник не ответил за отведённое время. Проверьте доступ к сайту и работает ли VPN для всего компьютера, а не только браузера.'
    if isinstance(reason,ConnectionRefusedError) or getattr(reason,'winerror',None)==10061:
        return 'CONNECTION_REFUSED: соединение отклонено сервером или прокси. Проверьте, запущен ли ваш прокси/VPN и верны ли его настройки.'
    if isinstance(reason,ConnectionResetError) or getattr(reason,'winerror',None)==10054:
        return 'CONNECTION_RESET: соединение прервано сервером или сетевым ПО. Проверьте VPN, прокси и правила брандмауэра для Python.'
    # Inspect only for classification; never echo raw exception text (may contain secrets).
    if 'tunnel connection failed' in str(reason).lower():
        return 'PROXY_TUNNEL: прокси не разрешил защищённое соединение с API. Проверьте системные настройки прокси/VPN; браузер и Python могут использовать разные маршруты.'
    return 'NETWORK: ошибка сетевого соединения Python. Проверьте базовый URL, системный прокси/VPN и доступ Python в брандмауэре. Причина пока не установлена.'
