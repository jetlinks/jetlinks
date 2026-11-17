# Jet Links 物联网基础平台
[![Maven Central](https://img.shields.io/maven-central/v/org.jetlinks/jetlinks.svg)](http://search.maven.org/#search%7Cga%7C1%7Cjetlinks)
[![Maven metadata URL](https://img.shields.io/maven-metadata/v/https/oss.sonatype.org/content/repositories/snapshots/org/jetlinks/jetlinks/maven-metadata.xml.svg)](https://oss.sonatype.org/content/repositories/snapshots/org/jetlinks/jetlinks)

```bash
----jetlinks
-------|--------jetlinks-core        #核心模块,统一API
-------|--------jetlinks-supports    #默认功能实现
-------|--------rule-engine          #规则引擎

```

请先在github中添加[SSH Key](https://github.com/settings/keys)
```bash
$ git clone --recursive git@github.com:jetlinks/jetlinks.git
```


# 1.3 SNAPSHOT 自动发布

`1.3` 的父仓库推送，以及三个子仓库合并后的通知，统一触发 `.github/workflows/maven-publish.yml`。
构建启动时固定父仓库与 `jetlinks-core`、`jetlinks-supports`、`rule-engine` 的 `1.3` 最新提交，
由 Maven reactor 按依赖顺序发布。较早的通知不会要求回退到其来源提交；运行中的发布不会被新通知取消。
各模块必须继承相同的 `1.3.x-SNAPSHOT` 父版本，默认使用 Java 17，沿用跳过测试执行的发布策略。

子仓库需要 Actions Secret `JETLINKS_DISPATCH_TOKEN`：使用仅授权 `jetlinks/jetlinks` 的细粒度 PAT，
权限为 Actions 读写及默认 Metadata 只读；组织审批及 Token 有效期需保持可用。Maven 凭证只保存在父仓库，
继续使用 `MAVEN_USERNAME`、`MAVEN_PASSWORD`，不分发到子仓库。

手动运行时在 Actions 中选择 `1.3`；默认分支只注册调度入口。`snapshot-publication-*` 运行制品保存全部源码 SHA、
实际 reactor 版本和 Maven 上传结果，用于追溯或按 SHA 重建。发布成功要求每个 reactor 制品都上传至正确版本坐标。
CI 对子模块的检出只发生在 runner 中，不修改仓库记录的子模块指针；正式版本及本地递归检出仍使用 Git 中的固定指针。

# 查看演示
本项目为核心模块整合,无法直接运行. 要看演示效果[请看这里](https://github.com/jetlinks/jetlinks-community).
