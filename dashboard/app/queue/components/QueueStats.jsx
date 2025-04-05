"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock, FileStack, AlertCircle, Ban, Tag, CheckCircle, RefreshCcw } from "lucide-react";

export function QueueStats() {
  const [stats, setStats] = useState({
    total: 0,
    available: 0,
    errors: 0,
    delisted: 0,
    sold: 0,
    lastUpdated: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isErrorsLoading, setIsErrorsLoading] = useState(false);

  useEffect(() => {
    const fetchQueueStats = async () => {
      try {
        setIsLoading(true);
        const response = await fetch("http://localhost:8000/data/queue/stats");

        if (!response.ok) {
          throw new Error("Failed to fetch queue statistics");
        }

        const responseData = await response.json();

        // Check if response has the expected format
        if (responseData.status === "success" && responseData.data) {
          setStats({
            total: responseData.data.total || 0,
            available: responseData.data.available || 0,
            errors: responseData.data.errors || 0,
            delisted: responseData.data.delisted || 0,
            sold: responseData.data.sold || 0,
            lastUpdated: new Date(),
          });
        } else {
          throw new Error("Invalid response format from server");
        }
      } catch (err) {
        console.error("Error fetching queue stats:", err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchQueueStats();
  }, []);

  // Format date to a readable string
  const formatDate = (date) => {
    if (!date) return "Never updated";

    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  };

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Queue Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Loading queue statistics...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Queue Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-red-500">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Queue Statistics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard title="Total Listings" value={stats.total.toLocaleString()} icon={<FileStack className="h-5 w-5" />} />
          <StatCard title="Available" value={stats.available.toLocaleString()} icon={<CheckCircle className="h-5 w-5" />} color="text-green-500" />
          <StatCard
            title="Errors"
            value={isErrorsLoading ? "Loading..." : stats.errors.toLocaleString()}
            icon={<AlertCircle className="h-5 w-5" />}
            color="text-red-500"
            onClick={async () => {
              setIsErrorsLoading(true);
              const response = await fetch("http://localhost:8000/queue/errors/count");
              const data = await response.json();
              setStats({ ...stats, errors: data.results.count });
              setIsErrorsLoading(false);
            }}
          />
          <StatCard title="Delisted" value={stats.delisted.toLocaleString()} icon={<Ban className="h-5 w-5" />} color="text-amber-500" />
          <StatCard title="Sold Out" value={stats.sold.toLocaleString()} icon={<Tag className="h-5 w-5" />} color="text-blue-500" />
          <StatCard title="Last Updated" value={formatDate(stats.lastUpdated)} icon={<Clock className="h-5 w-5" />} />
        </div>
      </CardContent>
    </Card>
  );
}

// Reusable stat card component
function StatCard({ title, value, icon, onClick, color = "text-slate-700" }) {
  return (
    <div className="flex items-center p-4 rounded-lg bg-muted/50 hover:cursor-pointer" onClick={onClick}>
      <div className={`mr-4 ${color}`}>{icon}</div>
      <div>
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
}
