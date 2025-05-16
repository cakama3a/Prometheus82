// Піни та налаштування
const int CONTACT_PIN = 3;
const int SOLENOID_PIN = 2;
unsigned long PULSE_DURATION_US = 40000;  // 40 мс у мікросекундах

// Змінні стану
volatile bool windowActive = false, contactDetected = false, solenoidActive = false;
volatile unsigned long solenoidStartTime_us = 0;

void handleContact() {
    if (windowActive && !contactDetected) {
        Serial.write('S');
        contactDetected = true;
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(CONTACT_PIN, INPUT_PULLUP);
    pinMode(SOLENOID_PIN, OUTPUT);
    
    attachInterrupt(digitalPinToInterrupt(CONTACT_PIN), handleContact, FALLING);
    
    // Початкова ініціалізація соленоїда (чіткі імпульси)
    for (int i = 0; i < 3; i++) {
        digitalWrite(SOLENOID_PIN, HIGH);
        delay(PULSE_DURATION_US / 1000);  // Конвертуємо мікросекунди в мілісекунди
        digitalWrite(SOLENOID_PIN, LOW);
        delay(200);  // Пауза 200 мс для чітких ударів
    }
    
    Serial.write('R');  // Сигнал готовності
}

void loop() {
    if (Serial.available() > 0) {
        char cmd = Serial.read();
        
        if (cmd == 'T') {  // Активація соленоїда
            contactDetected = false;
            digitalWrite(SOLENOID_PIN, HIGH);
            solenoidStartTime_us = micros();
            solenoidActive = true;
            windowActive = true;
        }
        else if (cmd == 'P') {  // Зміна тривалості
            // Чекаємо два байти з таймаутом 50 мс
            unsigned long startTime = millis();
            while (Serial.available() < 2 && (millis() - startTime) < 50) {
                ; // Чекаємо
            }
            if (Serial.available() >= 2) {
                unsigned long duration_ms = (Serial.read() << 8) | Serial.read();
                PULSE_DURATION_US = duration_ms * 1000;
                Serial.write('A');
            }
            // Очищаємо буфер
            while (Serial.available() > 0) {
                Serial.read();
            }
        }
    }

    // Вимкнення соленоїда після закінчення імпульсу
    if (solenoidActive && (micros() - solenoidStartTime_us >= PULSE_DURATION_US)) {
        digitalWrite(SOLENOID_PIN, LOW);
        solenoidActive = false;
    }
}