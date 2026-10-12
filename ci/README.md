# CI 模板启用说明

[demo-tests.yml](demo-tests.yml) 是两个应用共用的 GitHub Actions 模板，目前**没有自动执行**。创建本次 PR 使用的 OAuth 凭据缺少 `workflow` 权限，GitHub 拒绝通过该凭据向 `.github/workflows/` 推送文件，所以将模板保存在本目录。

有工作流写入权限的维护者可以从仓库根目录执行：

```sh
mkdir -p .github/workflows
git mv ci/demo-tests.yml .github/workflows/test.yml
git add .github/workflows/test.yml
git commit -m "Enable demo test workflow"
```

使用具备工作流写入权限的凭据推送，并通过 PR 合入。启用时同步更新根 README 和本说明中的“尚未启用”状态。模板对 PR 和 `main` 更新运行 Python 3.12 / Node.js 22 的测试，仅申请 `contents: read`，不需要 API key、不访问外馆、不包含部署步骤。

在启用前，从仓库根目录手动验证：

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s step1/tests -p 'test_*.py' -v
node --test step1/tests/search.test.mjs
```

本地运行全部测试需要 Python 3.9–3.12；HTTP 检查会使用临时本机端口。
