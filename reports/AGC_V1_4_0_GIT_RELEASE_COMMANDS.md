# AGC v1.4.0 Git Release Commands

本清单定义了 `v1.4.0` 版本的安全发布顺序。默认不可执行，所有操作必须获得用户授权。

## A. 只读预检

```bash
git branch --show-current
git status
git diff --check
git rev-parse HEAD
```

## B. 用户授权后本地暂存与 commit

用户明确授权后，暂存所有在 `AGC_V1_4_0_COMMIT_FILE_LIST.txt` 中的变更并进行提交。

```bash
xargs -a reports/AGC_V1_4_0_COMMIT_FILE_LIST.txt git add
git commit -m "feat(governance): implement v1.4.0 complete release candidate
- Add runtime, workspace, evidence modules
- Include comprehensive test suites
- Generate phase 0/1/wave 2-4 and RC evidences
- Apply completeness correction"
```

## C. 用户授权后推送分支和创建 PR

```bash
git push -u origin agc-v1.4.0-phase0
gh pr create --title "v1.4.0 Release Candidate" --body "Please review." --base main --head agc-v1.4.0-phase0
```

## D. 合并 main 后验证

PR 合并到 main 后，在 main 分支上拉取最新代码并进行预发布测试。

```bash
git checkout main
git pull origin main
python -m unittest discover -s tests
```

## E. 用户再次授权后 Tag 与 Release

只有在 main 上验证精确提交且 CI 通过后，才可打 Tag。

```bash
git rev-parse HEAD
git tag -a v1.4.0 -m "Release v1.4.0"
git push origin v1.4.0
gh release create v1.4.0 --title "v1.4.0" --notes-file docs/CHANGELOG.md
```
