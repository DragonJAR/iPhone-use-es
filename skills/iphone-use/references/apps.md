# Buscar el bundle ID real de una app

Un bundle ID que ya se conoce y se ha verificado se puede lanzar directamente; no vuelvas a consultar el inventario de instalación en cada launch. Para una app habitual, busca primero sin red el directorio local con `pua_apps(source="catalog")`. Para una app desconocida, o cuando haya que distinguir la versión que el usuario tiene instalada de verdad, usa source=auto: primero las apps instaladas en el iPhone seleccionado, después el directorio local, y solo si sigue sin haber candidatos consulta Apple. No inventes un bundle ID a partir del nombre de la marca ni pruebes varios valores adivinados uno tras otro.

```json
{"query":"招商银行","source":"auto"}
```

Este ejemplo debe devolver `com.cmbchina.MPBBank`. Después de revisar el nombre, el editor y el origen del candidato, pasa bundle_id a `pua_launch_app`. Un arranque normal continúa con optimismo. Si el paso siguiente necesita información de una página desconocida, pon observe en ese mismo launch y mira de paso el primer plano real y la página de destino; no añadas una comprobación de arranque por defecto. La app principal 招商银行 y la app de tarjeta 掌上生活 son dos aplicaciones.

- `source=auto`: lee primero la lista de instalación del dispositivo seleccionado (caché local de 300 segundos) y la fusiona con el directorio local. El nombre o el alias exactos tienen prioridad; si hay una coincidencia exacta, no se mezclan candidatos por subcadena. Solo si no hay candidato local se llama a Apple.
- `source=installed`: consulta solo el iPhone seleccionado. Si falta el dispositivo seleccionado o la lectura falla, devuelve un diagnóstico que se puede ejecutar. Un alias de marca en inglés puede mapearse, mediante el directorio local, al bundle ID de la lista de instalación.
- `source=catalog`: consulta sin red este archivo y las 36 apps de `apps.json` ya contrastadas con una consulta a Apple. No consulta en absoluto el iPhone ni la red.
- `source=apple`: consulta la API pública de Apple para el país o la región de App Store indicados. Por defecto `country=cn`; se pueden indicar `hk`, `us` y otros. Devuelve candidatos de la tienda, lo que no significa que estén instalados en el teléfono del usuario.

`installed_verified=true` significa que la lista de instalación del dispositivo seleccionado confirmó el candidato. `installation_checked` indica si esta consulta llegó a obtener la lista de instalación (caché de cinco minutos como máximo); false no se puede interpretar por sí solo como «no instalada». En el candidato, `verified_at` es la hora en que se verificó el origen. La consulta solo devuelve las apps que coinciden; no devuelve el inventario completo del dispositivo. El inventario de instalación y la caché se guardan en un directorio de estado privado fuera del repositorio, con permiso 600. No se envían a Apple la información del dispositivo ni el inventario de instalación.

## API oficial de Apple

La [documentación de la Apple iTunes Search API](https://performance-partners.apple.com/search-api) describe `software`, el parámetro de país o región, JSON, la caché y el límite orientativo de unas 20 consultas por minuto. Esa interfaz pública consulta metadatos de apps del App Store y no necesita el Apple ID, la contraseña ni una clave de API del usuario:

```text
https://itunes.apple.com/search?term=招商银行&country=cn&media=software&entity=software&limit=10
https://itunes.apple.com/lookup?id=392899425&country=cn&entity=software
```

Busca primero por nombre y contrasta el editor y el producto reales; después refresca con un Lookup del `trackId` estable. La documentación oficial indica que la consulta por ID empareja mal con menos frecuencia. No elijas automáticamente el primer resultado de la búsqueda por nombre. `pua_apps` usa codificación de URL, un tiempo de espera de red de 5 segundos, un límite de tamaño de respuesta, restricciones de dominio, ruta y redirección HTTPS de Apple, una caché de 15 minutos y como máximo 18 peticiones nuevas por minuto, para no bloquearse mucho tiempo ni chocar una y otra vez con el límite. El script de refresco hace Lookup por lotes, por región, de los ID ya revisados.

```sh
python3 scripts/update_app_catalog.py --search "nombre de la app" --country cn
python3 scripts/update_app_catalog.py --refresh
```

La búsqueda solo imprime candidatos; no los añade sola al directorio. Quien mantiene el catálogo contrasta la página del App Store, el editor y el producto concreto antes de añadir el registro. El refresco solo actualiza los metadatos de tienda de registros ya revisados; si falta un ID o cambia el bundle ID, se detiene y conserva el directorio original.

## Alcance y fallos

La búsqueda de la tienda de Apple tiene límites por homónimos, región y apps retiradas. Una app interna de empresa, una compilación de desarrollo o una app que no está en la tienda pueden no existir. La [interfaz bundleIds de App Store Connect](https://developer.apple.com/documentation/appstoreconnectapi/get-v1-bundleids) solo puede listar los ID registrados por el propio equipo de desarrollador; no sirve como directorio de todas las apps de terceros. La lista de lo instalado en el dispositivo es la evidencia más directa de la app real del usuario.

En esta comprobación, `富途牛牛` no tenía la app de destino en la búsqueda de CN y solo en la consulta de HK se obtuvo `cn.futu.FutuTraderPhone`. Ante un resultado vacío, consulta primero `source=installed` o busca en la región de tienda real del usuario. No interpretes que una búsqueda regional no la encuentre como que no está instalada. También hay que contrastar por separado 飞书 y la versión internacional Lark, 微信 y 企业微信, y la edición normal frente a 极速版 o la edición de desarrollo.

Si la propia consulta MCP no está disponible, se puede leer la lista de instalación local con el comando fijo de Xcode (`--include-all-apps` tiene que conservarse: devicectl, por defecto, solo muestra apps de desarrollo), filtrar en local el nombre o el bundle ID de destino y lanzar. La observación que el paso siguiente necesite también puede juzgar de paso el estado del arranque. Escribe el archivo en un directorio privado fuera del repositorio; no guardes el inventario de instalación completo en el proyecto:

```sh
xcrun devicectl device info apps --device "<UDID del dispositivo seleccionado>" --include-all-apps --json-output "<directorio privado>/apps.json" --timeout 8
```

## Directorio verificado

La URL real de la API de Apple, el nombre en la tienda, el editor, el país o la región y la hora de verificación en UTC de cada registro están en [apps.json](apps.json). Aquí solo se listan la marca, el bundle ID y la tienda de verificación. Un registro de tienda no demuestra el estado de instalación en el dispositivo.

| App | bundle ID | Tienda verificada |
| --- | --- | --- |
| 微信 | `com.tencent.xin` | [CN](https://apps.apple.com/cn/app/id414478124) |
| 支付宝 | `com.alipay.iphoneclient` | [CN](https://apps.apple.com/cn/app/id333206289) |
| 淘宝 | `com.taobao.taobao4iphone` | [CN](https://apps.apple.com/cn/app/id387682726) |
| 京东 | `com.360buy.jdmobile` | [CN](https://apps.apple.com/cn/app/id414245413) |
| 拼多多 | `com.xunmeng.pinduoduo` | [CN](https://apps.apple.com/cn/app/id1044283059) |
| 小红书 | `com.xingin.discover` | [CN](https://apps.apple.com/cn/app/id741292507) |
| 抖音 | `com.ss.iphone.ugc.Aweme` | [CN](https://apps.apple.com/cn/app/id1142110895) |
| 快手 | `com.jiangjia.gif` | [CN](https://apps.apple.com/cn/app/id440948110) |
| 哔哩哔哩 | `tv.danmaku.bilianime` | [CN](https://apps.apple.com/cn/app/id736536022) |
| 微博 | `com.sina.weibo` | [CN](https://apps.apple.com/cn/app/id350962117) |
| QQ | `com.tencent.mqq` | [CN](https://apps.apple.com/cn/app/id444934666) |
| QQ音乐 | `com.tencent.QQMusic` | [CN](https://apps.apple.com/cn/app/id414603431) |
| 网易云音乐 | `com.netease.cloudmusic` | [CN](https://apps.apple.com/cn/app/id590338362) |
| 百度地图 | `com.baidu.map` | [CN](https://apps.apple.com/cn/app/id452186370) |
| 高德地图 | `com.autonavi.amap` | [CN](https://apps.apple.com/cn/app/id461703208) |
| 滴滴出行 | `com.xiaojukeji.didi` | [CN](https://apps.apple.com/cn/app/id554499054) |
| 美团 | `com.meituan.imeituan` | [CN](https://apps.apple.com/cn/app/id423084029) |
| 饿了么 | `me.ele.ios.eleme` | [CN](https://apps.apple.com/cn/app/id507161324) |
| 携程旅行 | `ctrip.com` | [CN](https://apps.apple.com/cn/app/id379395415) |
| 飞猪 | `com.taobao.travel` | [CN](https://apps.apple.com/cn/app/id453691481) |
| 铁路12306 | `cn.12306.rails12306` | [CN](https://apps.apple.com/cn/app/id564818797) |
| 百度网盘 | `com.baidu.netdisk` | [CN](https://apps.apple.com/cn/app/id547166701) |
| 腾讯会议 | `com.tencent.meeting` | [CN](https://apps.apple.com/cn/app/id1484048379) |
| 钉钉 | `com.laiwang.DingTalk` | [CN](https://apps.apple.com/cn/app/id930368978) |
| 飞书 | `com.bytedance.ee.lark` | [CN](https://apps.apple.com/cn/app/id1401729613) |
| 企业微信 | `com.tencent.ww` | [CN](https://apps.apple.com/cn/app/id1087897068) |
| 招商银行 | `com.cmbchina.MPBBank` | [CN](https://apps.apple.com/cn/app/id392899425) |
| 掌上生活 | `com.cmbchina.cmblife` | [CN](https://apps.apple.com/cn/app/id398453262) |
| 中国工商银行 | `com.icbc.iphoneclient` | [CN](https://apps.apple.com/cn/app/id423514795) |
| 中国建设银行 | `com.ccb.ccbDemo` | [CN](https://apps.apple.com/cn/app/id391965015) |
| 中国农业银行 | `com.bankabc.iphonerelease` | [CN](https://apps.apple.com/cn/app/id515651240) |
| 中国银行 | `com.boc.BOCMBCI` | [CN](https://apps.apple.com/cn/app/id399608199) |
| 雪球 | `com.xueqiu` | [CN](https://apps.apple.com/cn/app/id492180369) |
| 同花顺 | `cn.com.10jqka.IHexin` | [CN](https://apps.apple.com/cn/app/id303191318) |
| 东方财富 | `com.eastmoney.iphone` | [CN](https://apps.apple.com/cn/app/id423525686) |
| 富途牛牛 | `cn.futu.FutuTraderPhone` | [HK](https://apps.apple.com/hk/app/id592031984) |
