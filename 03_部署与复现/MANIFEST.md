# 交付文件清单

本文件登记提交包内可执行/可校验文件的体积与 SHA256。模型与测试集见 `../05_模型与测试集/05_模型与测试集.md`。

---

## 1 脚本

**表 1 脚本**

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| `scripts/build.sh` | 4,001 | `be30ae1755a9d5d16d98a92a59a52602ca0abd06f96a78125b5b28339917a72a` |
| `scripts/quantize.sh` | 1,835 | `067924ab4e0c48e4acbadecf11c997466138818c812815e85cf8b5268aac18e0` |
| `scripts/deploy.sh` | 4,191 | `e589d2cc6555998382a2d70499551284fa932f1a1158dafad41e3968c3d569e5` |
| `scripts/verify.sh` | 4,784 | `a9d6872eedf615f7d15635395f8abfa5afeb55c53b30f3a496f5885fb7e91b07` |

## 2 补丁

**表 2 补丁**

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| `patches/01-q4_1-repack.patch` | 22,900 | `0c959f7127538eea60375ba0a348996e984552cccb91687dd0be2d881e489f21` |
| `patches/02-concat-fastpath.patch` | 1,800 | `1ff2ad455af15c308f0a6d1eb6a07743fe0d892f5362ea9c0ce86d07aeb6b6e4` |
| `patches/03-gqa-fold.patch` | 8,695 | `7ee959f3be5dd92c9978c292e5cfd1ba78f1a31115e1a2491de6e0c5df1f3242` |
| `patches/04-q5k-repack.patch` | 40,221 | `888f3a750befd9d6fa99db3e433d1db5b66ec86042dd9669ee67fdc65ecb1ef1` |
| `patches/05-q6k-repack.patch` | 18,698 | `55f72d22567e93b918b6dd90706a6de9aa4deb130f82e7fa41f4bb27a31be6c8` |
| `patches/06-q3k-repack.patch` | 32,163 | `90137692039808d06498b11bcbb418b11ec14606b57bde33a8f105e33f4cf306` |
| `patches/07-chunk16-chunkmult.patch` | 1,453 | `32b6c8ef8254568d54affea0c8c5cf711ee69abff7c202b01589c1ca6bc49f11` |

## 3 二进制与源码包

**表 3 二进制与源码包**

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| `../07_源码与二进制/llama-bin-chunk16-4436a9f4.tar.gz` | 7,174,113 | `7c6ad1d7c57e3386072af0a0a1a2b1c30c56f47824ab90f3986acd98c3b4e0bf` |
| `../07_源码与二进制/llama-src-final-717a8ad8.tar.gz` | 38,596,499 | `064fdd6fe3dae085b38821c5310679193bd147fd41d0a5d561b3afee9348742d` |

## 4 校验方法

```bash
# 在 03_部署与复现/ 目录下
sha256sum scripts/*.sh patches/*.patch
# 在 07_源码与二进制/ 目录下
sha256sum *.tar.gz
```

输出须与表 1—表 3 完全一致。

---

*补丁 01—03 已合入源码包；04—06 是 K-quant 变体的重排补丁（扩展实验用，交付构建不含）；07 由 `build.sh` 自动应用。*
