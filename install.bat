@echo off
title WD14 Tagger Installation

echo Installing WD14 Tagger dependencies...
echo.

pip install -r requirements.txt

echo.
echo Installation completed!
echo.
echo If you want to use DeepDanbooru models, also run:
echo   pip install git+https://github.com/KichangKim/DeepDanbooru.git
echo.
echo If you want to use the WebUI features, make sure you have Gradio installed:
echo   pip install gradio
echo.
echo For TensorFlow models, you might also need:
echo   pip install tensorflow
echo.
echo For ONNX models, you might also need:
echo   pip install onnxruntime
echo.
echo Press any key to exit...
pause >nul