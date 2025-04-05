"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ReportTable({ selectedDate }) {
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!selectedDate) return;

      try {
        setIsLoading(true);
        const response = await fetch(`http://localhost:8000/analytics/report?date=${selectedDate}`);

        if (!response.ok) {
          throw new Error("Failed to fetch report data");
        }

        const jsonData = await response.json();
        setData(Array.isArray(jsonData.reports) ? jsonData.reports : []);
      } catch (err) {
        setError(err.message);
        console.error("Error fetching report data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [selectedDate]);

  if (!selectedDate) {
    return null;
  }

  if (isLoading) {
    return (
      <Card className="col-span-3 mt-4">
        <CardHeader>
          <CardTitle>Loading report data...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="col-span-3 mt-4">
        <CardHeader>
          <CardTitle>Error</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card className="col-span-3 mt-4">
        <CardHeader>
          <CardTitle>Report for {selectedDate}</CardTitle>
        </CardHeader>
        <CardContent>
          <p>No data available for this date.</p>
        </CardContent>
      </Card>
    );
  }

  // Format elapsed time from seconds to a more readable format
  const formatElapsedTime = (seconds) => {
    if (seconds < 60) {
      return `${seconds.toFixed(2)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };

  // Calculate success rate percentage
  const calculateSuccessRate = (success, total, errors) => {
    const denominator = total + errors;
    if (denominator === 0) return "0%";
    const rate = (success / denominator) * 100;
    return `${rate.toFixed(1)}%`;
  };

  // Get numerical success rate value for color coding
  const getSuccessRateValue = (success, total, errors) => {
    const denominator = total + errors;
    if (denominator === 0) return 0;
    return (success / denominator) * 100;
  };

  // Get color based on success rate percentage
  const getSuccessRateColor = (rateValue) => {
    if (rateValue < 50) return "text-red-500";
    if (rateValue < 80) return "text-amber-500";
    return "text-green-500";
  };

  // Get background color for progress bar

  // Get fill color for progress bar
  const getProgressBarFillColor = (rateValue) => {
    if (rateValue < 50) return "bg-red-500";
    if (rateValue < 80) return "bg-amber-500";
    return "bg-green-500";
  };

  // Calculate overall success rate
  const totalSuccess = data.reduce((sum, item) => sum + item.success_count, 0);
  const totalListings = data.reduce((sum, item) => sum + item.total_listings, 0);
  const totalErrors = data.reduce((sum, item) => sum + item.error_count, 0);
  const overallSuccessRateValue = getSuccessRateValue(totalSuccess, totalListings, totalErrors);

  return (
    <Card className="col-span-3 mt-4">
      <CardHeader>
        <CardTitle>Report for {selectedDate}</CardTitle>
        <div>
          <div className="flex gap-4 text-base">
            <div>
              <span className="font-medium">Sources: </span>
              <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium ring-1 ring-inset ring-muted-foreground/20">{data.length}</span>
            </div>
            <div>
              <span className="font-medium">Errors: </span>
              <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium ring-1 ring-inset ring-muted-foreground/20">{totalErrors}</span>
            </div>
            <div>
              <span className="font-medium">Total Listings: </span>
              <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium ring-1 ring-inset ring-muted-foreground/20">{totalListings}</span>
            </div>
            <div>
              <span className="font-medium">Time: </span>
              <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium ring-1 ring-inset ring-muted-foreground/20">{formatElapsedTime(data.reduce((sum, item) => sum + item.duration, 0))}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="py-3 px-4 text-left font-medium">Source</th>
                <th className="py-3 px-4 text-left font-medium">Total Listings</th>
                <th className="py-3 px-4 text-left font-medium">Errors</th>
                <th className="py-3 px-4 text-left font-medium">Duration</th>
                <th className="py-3 px-4 text-left font-medium">Success (%)</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item, index) => {
                const successRateValue = getSuccessRateValue(item.success_count, item.total_listings, item.error_count);
                const progressBarFillColor = getProgressBarFillColor(successRateValue);

                return (
                  <tr key={item.id} className={index % 2 === 0 ? "bg-muted/50" : ""}>
                    <td className="py-3 px-4">{item.source}</td>
                    <td className="py-3 px-4">{item.total_listings}</td>
                    <td className="py-3 px-4">{item.error_count}</td>
                    <td className="py-3 px-4">{formatElapsedTime(item.duration)}</td>
                    <td className="py-3 px-4">
                      <div className="w-full h-6 rounded-md overflow-hidden relative bg-muted">
                        <div className={`absolute top-0 left-0 h-full ${progressBarFillColor}`} style={{ width: `${Math.min(100, successRateValue)}%` }}></div>
                        <span className={`absolute inset-0 flex items-center justify-center text-xs font-medium z-10`}>{calculateSuccessRate(item.success_count, item.total_listings, item.error_count)}</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
