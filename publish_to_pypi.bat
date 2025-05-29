@echo off
echo 确保您已经设置 PyPI 账户信息！

REM 编译并打包
call build_package.bat

REM 发布到 PyPI
python -m twine upload dist/*

echo 发布完成！您的包现在应该可以通过 pip install movan_rpc 来安装。