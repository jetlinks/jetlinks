#!/usr/bin/env bash
mvn clean install -DskipTests
cd jetlinks-protocol
mvn clean install -DskipTests
cd ../jetlinks-registry
mvn clean install -DskipTests
cd ../jetlinks-gateway
mvn clean install -DskipTests
