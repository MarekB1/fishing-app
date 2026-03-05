import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ScoreboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.competition_id = self.scope["url_route"]["kwargs"]["competition_id"]
        self.group_name = f"competition_{self.competition_id}"

        # Pozn.: autentifikáciu/práva riešime jednoducho tým,
        # že WS je dostupný len logged-in userom (AuthMiddlewareStack).
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def catch_created(self, event):
        # Pošli jednoduchý event do browsera
        await self.send(text_data=json.dumps({"event": "catch_created"}))

    # (voliteľné neskôr) approve/reject
    async def catch_moderated(self, event):
        await self.send(text_data=json.dumps({"event": "catch_moderated"}))