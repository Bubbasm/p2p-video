# Práctica 3

Implementación de un cliente multimedia P2P en `Python`, con posibilidad de *streaming* de vídeo y de video-conferencia (entre 2 clientes, sin audio), por Bhavuk Sikka y Samuel de Lucas Maroto.

## Requisitos para ejecutar
- `python >= 3.6` con los siguientes módulos
  - `pillow`
  - `opencv-python`
  - `appjar`
  - `pyscreenshot`
  - `numpy`

> NOTA: como requisito adicional, será necesaria la creación del directorio `./imgs/`, conteniendo el archivo `webcam.gif`. Este archivo es necesario para iniciar el módulo de captura de vídeo. 

## Cómo ejecutar el programa
Para ejecutar el cliente, bastará con el comando:
```sh
$ python src/cliente.py
```

También podemos simular pérdida de paquetes con la opción `-pl` o `--packet_loss` indicando el porcentaje de paquetes que se perderán (número entre 0 y 1):
```sh
$ python src/cliente.py --packet_loss <porcentaje>
```
Esta opción impide el envío de algunos paquetes (aproximadamente, el porcentaje indicado), simulando así congestión de la red (podemos ver cortes en la recepción en caso de la V0, incluso pérdida de calidad en caso de usar V1).

> AVISO: Si simulamos una pérdida de paquetes muy alta, el buffer tardará mucho en llenarse, y parecerá que no funciona. Debemos esperar pacientemente para comenzar a ver los paquetes reproduciéndose. La comunicación se cortará si estamos intentando llenar el buffer y pasan 10 segundos (ya que la calidad de red sería demasiado mala).
