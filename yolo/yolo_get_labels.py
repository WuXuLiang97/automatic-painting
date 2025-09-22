from ultralytics import YOLO

model = YOLO("model_data\\best.pt")
print("类别名:", model.names)
with open("model_data\\main_classes.txt", "w") as f:
    for idx in range(len(model.names)):
        f.write(f"{model.names[idx]}\n")

min_map_model = YOLO("model_data\\min_map_best.pt")
print("小地图类别名:", min_map_model.names)
with open("model_data\\min_map_classes.txt", "w") as f:
    for idx in range(len(min_map_model.names)):
        f.write(f"{model.names[idx]}\n")
