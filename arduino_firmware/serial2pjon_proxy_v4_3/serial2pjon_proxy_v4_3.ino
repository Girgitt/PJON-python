#define MAX_PACKETS 4
#include <PJON.h>
#include <SoftwareSerial.h>

SoftwareSerial sSerial(10, 11); // RX, TX


//PJON<ThroughHardwareSerialRs485AutoTx> bus(45);
//PJON<ThroughHardwareSerialRs485AutoTx> bus_hw(35);

PJON<ThroughHardwareSerial> bus(45);
PJON<ThroughHardwareSerial> bus_hw(35);

long start_ts;
int last_received_address = 0;

void setup() {
  pinModeFast(13, OUTPUT);
  digitalWriteFast(13, LOW); // Initialize LED 13 to be off
 
  //bus.set_pins(2, 1);
  //bus.set_rx_vcc_pin(12);
  bus.set_receiver(receiver_function);
  bus_hw.set_receiver(receiver_function_hw);
  //bus_hw.set_error(error_handler_hw);
  
  //bus.begin();
  Serial.begin(115200);
  sSerial.begin(76800);
  //bus.strategy.set_serial(&sSerial);
  bus_hw.strategy.set_serial(&Serial);
  
  
  
  //bus.include_sender_info(false);
    //bus.set_acknowledge(false);
   //bus_hw.set_acknowledge(true);
  //bus.set_packet_auto_deletion(true);
  //bus.set_router(false);

  
  
  //bus.send_repeatedly(44, "B1234567891234567890", 20, 100000); // Send B to device 44 every second
  start_ts = millis();
}


void receiver_function(uint8_t *payload, uint8_t length, const PacketInfo &packet_info) {
  if(payload[0] == 'C') {
    //Serial.println("BLINK");
    digitalWriteFast(13, HIGH);
    delay(1);
    digitalWriteFast(13, LOW);
    delay(1);
    digitalWriteFast(13, HIGH);
    delay(1);
    digitalWriteFast(13, LOW);
  }
}

void receiver_function_hw(uint8_t *payload, uint8_t length, const PacketInfo &packet_info) {
  if(payload[0] == 'C') {
   last_received_address = packet_info.sender_id;
    //Serial.println("BLINK");
    digitalWriteFast(13, HIGH);
    delay(1);
    digitalWriteFast(13, LOW);
    delay(1);
    digitalWriteFast(13, HIGH);
    delay(1);
    digitalWriteFast(13, LOW);
  }
}

void error_handler_hw(uint8_t code, uint8_t data) {
    Serial.print("err:");
    Serial.println(code);
    Serial.println(data);
}

boolean fired=false;

boolean updated=false;
long last_update_ts = 0; 

void loop() {
    if (millis() % 5 < 2){
      if(!updated){
        updated = true;
        last_update_ts=millis();
        //bus.update();
        bus_hw.update();
      };
  }else{
    updated = false;
    };
        //bus.update();
        //bus_hw.update();    
  //bus.receive(100);
  bus_hw.receive(100);
  
  if (millis() % 500 < 100){
      if(!fired){
        fired = true;
        
        start_ts=millis();
        
        digitalWriteFast(13, HIGH);
        delay(1);
        digitalWrite(13, LOW);
        
        //bus.send(44, "B12345689012345678901234567789", 30);
        //bus.send(44, "B123456789", 10);
        if(last_received_address > 0){
          bus_hw.send(last_received_address, "B123456789", 10);
        };
      };
  }else{
    fired = false;
    };
};
