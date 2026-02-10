---
description: 发版流程 - 打包 Mac DMG 并上传到 Gitee Release
---

# 发版流程

## 前置条件
- `$GITEE_TOKEN` 环境变量已设置（在 `~/.zshrc` 中配置）
- Gitee 仓库: `cong_wa/mobile-mcp`
- 工作目录: `/Users/wang/code/gitee/mobile-mcp`

## 步骤

### 1. 确认版本号并更新 setup.py
- 查看当前版本: `grep 'version=' setup.py`
- 查看最新 tag: `git tag --sort=-v:refname | head -1`
- 根据变更类型决定新版本号（major.minor.patch）
- 更新 `setup.py` 中的 `version=` 字段

### 2. 提交所有变更
```bash
git add -A
git commit -m "feat: <变更描述>"
```

### 3. 创建 Git Tag 并推送
```bash
git tag -a v<VERSION> -m "v<VERSION>: <描述>"
git push origin master
git push origin v<VERSION>
```

### 4. 打包 Mac DMG
// turbo
```bash
cd /Users/wang/code/gitee/mobile-mcp/frontend && npm run make:full
```
产物路径: `frontend/out/make/Mobile Agent-0.1.0-arm64.dmg`

### 5. 创建 Gitee Release
```bash
curl -s -X POST "https://gitee.com/api/v5/repos/cong_wa/mobile-mcp/releases" \
  -d "access_token=$GITEE_TOKEN" \
  -d "tag_name=v<VERSION>" \
  -d "name=v<VERSION>: <标题>" \
  --data-urlencode "body=<release notes>" \
  -d "target_commitish=master"
```
记录返回的 release `id`。

### 6. 上传 DMG 到 Release
Gitee 限制单文件 100MB，DMG 通常 ~196MB，需要分卷上传：

```bash
# 分卷（每卷 95MB）
cd /Users/wang/code/gitee/mobile-mcp/frontend/out/make
split -b 95m "Mobile Agent-0.1.0-arm64.dmg" "Mobile-Agent-v<VERSION>-arm64.dmg.part"

# 逐个上传分卷
for f in Mobile-Agent-v<VERSION>-arm64.dmg.part*; do
  curl -s -X POST "https://gitee.com/api/v5/repos/cong_wa/mobile-mcp/releases/<RELEASE_ID>/attach_files" \
    -H "Content-Type: multipart/form-data" \
    -F "access_token=$GITEE_TOKEN" \
    -F "file=@$f"
  echo "上传完成: $f"
done

# 清理临时分卷
rm -f Mobile-Agent-v<VERSION>-arm64.dmg.part*
```

### 7. 更新 Release 说明（加入合并命令）
```bash
curl -s -X PATCH "https://gitee.com/api/v5/repos/cong_wa/mobile-mcp/releases/<RELEASE_ID>" \
  -d "access_token=$GITEE_TOKEN" \
  -d "tag_name=v<VERSION>" \
  -d "name=v<VERSION>: <标题>" \
  --data-urlencode "body=<release notes>

## Mac 安装包
下载全部分卷后合并：
\`\`\`bash
cat Mobile-Agent-v<VERSION>-arm64.dmg.parta* > Mobile-Agent-v<VERSION>-arm64.dmg
\`\`\`"
```

### 8. 验证
- 访问 https://gitee.com/cong_wa/mobile-mcp/releases/tag/v<VERSION> 确认分卷文件和说明
