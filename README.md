# Jet Links 物联网基础平台
[![Maven Central](https://img.shields.io/maven-central/v/org.jetlinks/jetlinks.svg)](http://search.maven.org/#search%7Cga%7C1%7Cjetlinks)
[![Maven metadata URL](https://img.shields.io/maven-metadata/v/https/oss.sonatype.org/content/repositories/snapshots/org/jetlinks/jetlinks/maven-metadata.xml.svg)](https://oss.sonatype.org/content/repositories/snapshots/org/jetlinks/jetlinks)

```bash
----jetlinks
-------|--------coap-codec           #CoAP协议编码解码包
-------|--------device-simulator     #设备模拟器，模拟设备消息收发以及压力测试
-------|--------jetlinks-cloud       #基于spring-cloud,hsweb的云平台实现
-------|--------jetlinks-gateway     #设备网关底层,基于vertx提供统一的MQTT,udp网关支持
-------|--------jetlinks-core        #核心模块,统一API
-------|--------jetlinks-registry-redis    #设备注册中心的redis实现
-------|--------netty-mqtt-client    #基于netty的mqtt客户端实现
-------|--------rule-engine          #规则引擎

```

请先在github中添加[SSH Key](https://github.com/settings/keys)
```bash
$ git clone --recursive git@github.com:jetlinks/jetlinks.git
```


# 查看演示
本项目为核心模块整合,无法直接运行. 要看演示效果[请看这里](https://github.com/jetlinks/jetlinks-platform).