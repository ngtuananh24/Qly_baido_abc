import json
import threading
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
import paho.mqtt.client as mqtt

app = Flask(__name__)

# Cấu hình MySQL
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "admin",
    "database": "qly_baido"
}

# Global state lưu trạng thái của 6 vị trí đỗ xe và góc servo
parking_spots = {
    "left": [0, 0, 0],   # cb1, cb2, cb3
    "right": [0, 0, 0]   # cb4, cb5, cb6
}
servo_angle = 0  # góc servo nhận từ cảm biến

# Cấu hình MQTT
MQTT_BROKER = "f03f9ea0745245ce996d7f35c388d455.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "ngtuananh24"
MQTT_PASSWORD = "Anh2407@"


# Hàm lưu vào MySQL (loại bỏ servo_angle)
def save_to_mysql(cb_values):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        sql = """INSERT INTO sensor_data (cb1, cb2, cb3, cb4, cb5, cb6)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, cb_values)  # Không còn servo_angle
        conn.commit()
        cursor.close()
        conn.close()
        print("✔ Dữ liệu đã lưu vào MySQL:", cb_values)
    except mysql.connector.Error as err:
        print("Lỗi MySQL:", err)


subscribed = False  # Biến cờ để kiểm tra


def on_connect(client, userdata, flags, rc):
    global subscribed
    print("✅ Đã kết nối MQTT với mã:", rc)

    if not subscribed:  # Nếu chưa subscribe, mới thực hiện
        client.subscribe("test/cb", qos=0)
        subscribed = True
        print("📡 Đã đăng ký nhận dữ liệu từ test/cb")


def on_message(client, userdata, msg):
    global parking_spots, servo_angle, status_cua
    if msg.topic == "test/cb":
        try:
            data = json.loads(msg.payload.decode())
            print("📩 Dữ liệu nhận từ MQTT:", data)  # Debug xem dữ liệu đúng chưa
            cb_values = [
                int(data.get("cb1", 0)),
                int(data.get("cb2", 0)),
                int(data.get("cb3", 0)),
                int(data.get("cb4", 0)),
                int(data.get("cb5", 0)),
                int(data.get("cb6", 0))
            ]
            print("✅ Dữ liệu sau khi xử lý:", cb_values)  # Debug dữ liệu trước khi lưu

            parking_spots["left"] = cb_values[:3]
            parking_spots["right"] = cb_values[3:]

            if "servo" in data:
                servo_angle = int(data["servo"])
            # Gọi hàm lưu vào MySQL
            save_to_mysql(cb_values)

        except Exception as e:
            print("❌ Lỗi khi xử lý JSON:", e)


# Khởi tạo MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)


def mqtt_loop():
    mqtt_client.loop_forever()


mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.daemon = True
mqtt_thread.start()


@app.route('/')
def index():
    return render_template('index.html', parking_spots=parking_spots, servo_angle=servo_angle)


@app.route('/control_servo', methods=['POST'])
def control_servo():
    state = request.form.get('state')
    mqtt_client.publish("test/servo", state)
    print("Gửi lệnh servo:", state)
    return redirect(url_for('index'))


@app.route('/display_lcd', methods=['POST'])
def display_lcd():
    text = request.form.get('text')
    mqtt_client.publish("test/lcd", text)
    print("Gửi text LCD:", text)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
