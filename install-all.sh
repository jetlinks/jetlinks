#!/usr/bin/env bash
mvn clean deploy -DskipTests
cd coap-codec
mvn clean deploy -DskipTests
cd ../jetlinks-protocol
mvn clean deploy -DskipTests
cd ../jetlinks-registry
mvn clean deploy -DskipTests
cd ../jetlinks-gateway
mvn clean deploy -DskipTests