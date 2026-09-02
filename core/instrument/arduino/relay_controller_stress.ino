#include <string.h>

const byte RELAY_1_PIN = 2;
const byte RELAY_2_PIN = 3;
const bool ACTIVE_LOW = true;

bool relay1Active = false;
bool relay2Active = false;
char commandBuffer[32];
byte commandLength = 0;

void setRelayPin(byte pin, bool active) {
	digitalWrite(pin, active == ACTIVE_LOW ? LOW : HIGH);
}

void turnOffAll() {
	relay1Active = false;
	relay2Active = false;
	setRelayPin(RELAY_1_PIN, false);
	setRelayPin(RELAY_2_PIN, false);
}

void selectDevice(byte device) {
	turnOffAll();
	if (device == 2) {
		relay1Active = true;
		relay2Active = true;
		setRelayPin(RELAY_1_PIN, true);
		setRelayPin(RELAY_2_PIN, true);
	}
}

void processCommand(char *command) {
	if (!strcmp(command, "HELLO")) {
		Serial.println("OK RELAY_V1");
		return;
	}

	if (!strcmp(command, "OFF ALL")) {
		turnOffAll();
		Serial.println("OK OFF ALL");
		return;
	}

	if (!strcmp(command, "SELECT A")) {
		selectDevice(1);
		Serial.println("OK SELECT A");
		return;
	}

	if (!strcmp(command, "SELECT B")) {
		selectDevice(2);
		Serial.println("OK SELECT B");
		return;
	}

	if (!strcmp(command, "STATUS?")) {
		Serial.print("STATUS ");
		Serial.print(relay1Active ? 1 : 0);
		Serial.print(" ");
		Serial.println(relay2Active ? 1 : 0);
		return;
	}

	turnOffAll();
	Serial.println("ERROR comando no valido");
}

void setup() {
	pinMode(RELAY_1_PIN, OUTPUT);
	pinMode(RELAY_2_PIN, OUTPUT);
	turnOffAll();
	Serial.begin(115200);
}

void loop() {
	while (Serial.available()) {
		char character = Serial.read();
		if (character == '\r') {
			continue;
		}

		if (character == '\n') {
			commandBuffer[commandLength] = 0;
			if (commandLength) {
				processCommand(commandBuffer);
			}
			commandLength = 0;
		} else if (commandLength < 31) {
			commandBuffer[commandLength++] = character;
		} else {
			commandLength = 0;
			turnOffAll();
			Serial.println("ERROR comando demasiado largo");
		}
	}
}