---
description: 发版流程 - 打包 Mac DMG 并上传到 Gitee Release
---

# 发版流程

同时发布到 Gitee 和 GitHub 双平台。

## 前置条件
- `$GITEE_TOKEN` 环境变量已设置（在 `~/.zshrc` 中配置）
- `$GITHUB_TOKEN` 环境变量已设置（在 `~/.zshrc` 中配置，classic token 需 repo 权限）
- gh CLI 路径: `/tmp/gh/gh_2.67.0_macOS_arm64/bin/gh`（或系统安装的 `gh`）
- Git remotes:
  - `origin` → `git@gitee.com:cong_wa/mobile-mcp.git`
  - `github` → `https://github.com/congwa/mobile-agent.git`
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

### 3. 创建 Git Tag 并推送到双平台
```bash
git tag -a v<VERSION> -m "v<VERSION>: <描述>"
# 推送到 Gitee
git push origin master
git push origin v<VERSION>
# 推送到 GitHub
git push github master
git push github v<VERSION>
```

### 4. 打包 Mac DMG
// turbo
```bash
cd /Users/wang/code/gitee/mobile-mcp/frontend && npm run make:full
```
产物路径: `frontend/out/make/Mobile Agent-0.1.0-arm64.dmg`

### 5. 创建 GitHub Release 并上传 DMG（无文件大小限制）
```bash
export GH_TOKEN="$GITHUB_TOKEN"
gh release create v<VERSION> --repo congwa/mobile-agent \
  --title "v<VERSION>: <标题>" \
  --notes "<release notes>" \
  "/Users/wang/code/gitee/mobile-mcp/frontend/out/make/Mobile Agent-0.1.0-arm64.dmg"
```
注：如果 `gh` 不在 PATH 中，使用 `/tmp/gh/gh_2.67.0_macOS_arm64/bin/gh`。

### 6. 创建 Gitee Release
```bash
curl -s -X POST "https://gitee.com/api/v5/repos/cong_wa/mobile-mcp/releases" \
  -d "access_token=$GITEE_TOKEN" \
  -d "tag_name=v<VERSION>" \
  -d "name=v<VERSION>: <标题>" \
  --data-urlencode "body=<release notes>" \
  -d "target_commitish=master"
```
记录返回的 release `id`。

### 7. 上传 DMG 到 Gitee Release（分卷）
Gitee 限制单文件 100MB，DMG 通常 ~196MB，需要分卷上传：

```bash
cd /Users/wang/code/gitee/mobile-mcp/frontend/out/make
split -b 95m "Mobile Agent-0.1.0-arm64.dmg" "Mobile-Agent-v<VERSION>-arm64.dmg.part"

for f in Mobile-Agent-v<VERSION>-arm64.dmg.part*; do
  curl -s -X POST "https://gitee.com/api/v5/repos/cong_wa/mobile-mcp/releases/<RELEASE_ID>/attach_files" \
    -H "Content-Type: multipart/form-data" \
    -F "access_token=$GITEE_TOKEN" \
    -F "file=@$f"
  echo "上传完成: $f"
done

rm -f Mobile-Agent-v<VERSION>-arm64.dmg.part*
```

### 8. 更新 Gitee Release 说明（加入合并命令）
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

### 9. 验证
- Gitee: https://gitee.com/cong_wa/mobile-mcp/releases/tag/v<VERSION>
- GitHub: https://github.com/congwa/mobile-agent/releases/tag/v<VERSION>
