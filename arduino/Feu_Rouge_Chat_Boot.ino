#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

const char* ssid = "CAFE AFRICA";      
const char* password = "africa000";

const String server = "http://192.168.0.100:5000/command"; // Flask Python

// LEDs0000000
int red1 = D0;
int red2 = D5;
int yellow1 = D1;
int yellow2 = D6;
int green1 = D2;
int green2 = D7;

void setup() {
  Serial.begin(115200);

  pinMode(red1, OUTPUT);
  pinMode(red2, OUTPUT);
  pinMode(yellow1, OUTPUT);
  pinMode(yellow2, OUTPUT);
  pinMode(green1, OUTPUT);
  pinMode(green2, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connexion au WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnecté !");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, server);
    int httpCode = http.GET();

    if (httpCode == 200) {
      String payload = http.getString();
      Serial.println(payload);

      // --- LED rouges ---
      if (payload.indexOf("red1_on") >= 0) digitalWrite(red1, HIGH);
      if (payload.indexOf("red1_off") >= 0) digitalWrite(red1, LOW);

      if (payload.indexOf("red2_on") >= 0) digitalWrite(red2, HIGH);
      if (payload.indexOf("red2_off") >= 0) digitalWrite(red2, LOW);

      // --- LED jaunes/orange ---
      if (payload.indexOf("yellow1_on") >= 0) digitalWrite(yellow1, HIGH);
      if (payload.indexOf("yellow1_off") >= 0) digitalWrite(yellow1, LOW);

      if (payload.indexOf("yellow2_on") >= 0) digitalWrite(yellow2, HIGH);
      if (payload.indexOf("yellow2_off") >= 0) digitalWrite(yellow2, LOW);

      // --- LED vertes ---
      if (payload.indexOf("green1_on") >= 0) digitalWrite(green1, HIGH);
      if (payload.indexOf("green1_off") >= 0) digitalWrite(green1, LOW);

      if (payload.indexOf("green2_on") >= 0) digitalWrite(green2, HIGH);
      if (payload.indexOf("green2_off") >= 0) digitalWrite(green2, LOW);

    } else {
      Serial.print("Erreur HTTP : ");
      Serial.println(httpCode);
    }

    http.end();
  }

  delay(500); // rafraîchissement toutes les 0,5s
}
