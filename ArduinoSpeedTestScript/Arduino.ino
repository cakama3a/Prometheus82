void setup() {
    Serial.begin(115200);
}

void loop() {
    if (Serial.available() > 0) {
        Serial.read();
        Serial.write('R');
    }
}