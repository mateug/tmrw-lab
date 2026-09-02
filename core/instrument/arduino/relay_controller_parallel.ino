#include <string.h>

const byte NUM_RELAYS = 6;
const byte NUM_DEVICES = 7;
const byte RELAY_PINS[NUM_RELAYS] = {2, 3, 4, 5, 6, 7}; // IN1->D2 ... IN6->D7
// Esta placa activa los relés con nivel LOW.
const bool ACTIVE_LOW = true;

bool relayActive[NUM_RELAYS] = {false, false, false, false, false, false};
char commandBuffer[32];
byte commandLength = 0;

void setRelayPin(byte pin, bool active) {
	if (ACTIVE_LOW) {
		digitalWrite(pin, active ? LOW : HIGH);
	} else {
		digitalWrite(pin, active ? HIGH : LOW);
	}
}

void turnOffAll() {
	for (byte i = 0; i < NUM_RELAYS; i++) {
		relayActive[i] = false;
		setRelayPin(RELAY_PINS[i], false);
	}
}

void selectDevice(byte device) {
	turnOffAll();
	if (device < 1 || device > NUM_DEVICES) return;

	byte L = 1;
	byte R = NUM_DEVICES;

	// Algoritmo de conmutación de árbol binario inorden
	while (L < R) {
		byte rele = (L + R) / 2;
		if (device <= rele) {
			R = rele; // Permanece en NC (relé inactivo)
		} else {
			relayActive[rele - 1] = true;
			setRelayPin(RELAY_PINS[rele - 1], true); // Conmuta a NO
			L = rele + 1;
		}
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

	// Procesar comandos SELECT A hasta SELECT G
	if (!strncmp(command, "SELECT ", 7) && strlen(command) == 8) {
		char devChar = command[7];
		if (devChar >= 'A' && devChar < ('A' + NUM_DEVICES)) {
			byte deviceIndex = devChar - 'A' + 1;
			selectDevice(deviceIndex);
			Serial.print("OK ");
			Serial.println(command);
			return;
		}
	}

	if (!strcmp(command, "STATUS?")) {
		Serial.print("STATUS");
		for (byte i = 0; i < NUM_RELAYS; i++) {
			Serial.print(" ");
			Serial.print(relayActive[i] ? 1 : 0);
		}
		Serial.println();
		return;
	}

	turnOffAll();
	Serial.println("ERROR comando no valido");
}

void setup() {
	for (byte i = 0; i < NUM_RELAYS; i++) {
		pinMode(RELAY_PINS[i], OUTPUT);
	}
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