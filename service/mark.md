导出onnx
paddle2onnx --model_dir .\PP-OCRv5_mobile_det --model_filename inference.json --params_filename inference.pdiparams --save_file .\PP-OCRv5_mobile_det\det.onnx --opset_version 11 --enable_onnx_checker True
paddle2onnx --model_dir .\PP-OCRv5_mobile_rec --model_filename inference.json --params_filename inference.pdiparams --save_file .\PP-OCRv5_mobile_rec\rec.onnx --opset_version 11 --enable_onnx_checker True

pyinstaller .\ocr_server.spec

pyinstaller app_server.py `
  --name ocr_server `
  --noconfirm --clean `
  --add-data "PP-OCRv5_mobile_det\\det.onnx;PP-OCRv5_mobile_det" `
  --add-data "PP-OCRv5_mobile_rec\\rec.onnx;PP-OCRv5_mobile_rec" `
  --add-data "PP-OCRv5_mobile_rec\\keys.txt;PP-OCRv5_mobile_rec" `
  --add-data "yolo\\model_data\\best.onnx;yolo\\model_data" `
  --add-data "yolo\\model_data\\min_map_best.onnx;yolo\\model_data" `
  --add-data "工具人.ini;." `
  --noconsole `


生成 dist\\ocr_server\\ocr_server.exe

Onefile（可选）
加 --onefile，但启动慢：
pyinstaller app_server.py ...同上参数... --onefile

精简体积（可选）
生成的 ocr_server.spec 中添加 excludes=['paddle','torch']：
修改后：pyinstaller ocr_server.spec
