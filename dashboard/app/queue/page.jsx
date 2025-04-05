"use client";

import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { QueueStats, JsonUrlUpload, QueueErrors } from "./components";
import { Button } from "@/components/ui/button";
import { Cloud } from "lucide-react";

function QueuePage() {
  const [activeTab, setActiveTab] = useState("stats");
  const [syncing, setSyncing] = useState(false);
  const [syncingMessage, setSyncingMessage] = useState("");

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Queue Management</h1>

      <Tabs defaultValue="stats" className="w-full" onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-md grid-cols-2 mb-8">
          <TabsTrigger value="stats">Queue Stats</TabsTrigger>
          <TabsTrigger value="upload">Upload Data</TabsTrigger>
        </TabsList>
        <TabsContent value="stats" className="mt-0 flex flex-col gap-y-6">
          <Button
            className="w-fit cursor-pointer"
            variant="outline"
            onClick={() => {
              setSyncing(true);
              fetch("http://localhost:8000/queue/sync")
                .then((res) => res.json())
                .then((data) => {
                  const message = `${data.count} listings have been updated (${data.errors} errors, ${data.not_available} not available)`;
                  setSyncingMessage(message);
                  setSyncing(false);
                });
            }}
          >
            <div className="flex items-center gap-2">
              <Cloud className="h-4 w-4" />
              Sync Queues with Listings
            </div>
            <p className="text-sm text-muted-foreground">{syncing ? "Syncing..." : syncingMessage}</p>
          </Button>
          <QueueStats />
          <QueueErrors />
        </TabsContent>

        <TabsContent value="upload" className="mt-0">
          <div className="grid gap-8 md:grid-cols-2">
            <JsonUrlUpload />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default QueuePage;
