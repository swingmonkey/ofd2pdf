# ofdrw 后端构建说明

本项目使用 [ofdrw/ofdrw](https://github.com/ofdrw/ofdrw) 作为底层库，将 OFD 转为 PDF。

## 前置要求

- Java 8+
- Maven 3.6+

## 构建

```bash
cd scripts/ofdrw
mvn package
```

构建完成后，jar 位于：

```text
target/ofdrw-converter-cli-0.1.0.jar
```

## 放置到 ofd2pdf 项目中

```bash
cp target/ofdrw-converter-cli-0.1.0.jar ../../bin/ofdrw-converter.jar
```

或使用环境变量：

```bash
export OFD2PDF_OFDRW_JAR=/path/to/ofdrw-converter.jar
```

## 使用

```bash
ofd2pdf input.ofd -o output.pdf --backend ofdrw
```

## 说明

`ofdrw-full` 已包含 `ofdrw-converter` 模块，因此直接依赖 `ofdrw-full` 即可。
