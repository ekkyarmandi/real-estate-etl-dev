"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ListingsChart({ onDateSelect }) {
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeIndex, setActiveIndex] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/listings-count`, {
          cache: "force-cache",
        });

        if (!response.ok) {
          throw new Error("Failed to fetch data");
        }

        const jsonData = await response.json();

        // Transform the data from object to array format for Recharts
        const formattedData = Object.entries(jsonData).map(([date, count]) => {
          // Format the date to be more readable
          const formattedDate = new Date(date).toLocaleDateString("en-US", {
            month: "short",
            year: "numeric",
          });

          return {
            date: formattedDate,
            count: count,
            fullDate: date, // Keep the original date for sorting and API calls
          };
        });

        // Sort the data by date
        formattedData.sort((a, b) => new Date(a.fullDate) - new Date(b.fullDate));

        setData(formattedData);
      } catch (err) {
        setError(err.message);
        console.error("Error fetching data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleBarClick = (data, index) => {
    setActiveIndex(index);
    if (onDateSelect && data && data.fullDate) {
      onDateSelect(data.fullDate);
    }
  };

  if (isLoading) {
    return (
      <Card className="col-span-3 h-[400px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="col-span-3 h-[400px] flex items-center justify-center">
        <p className="text-red-500">Error: {error}</p>
      </Card>
    );
  }

  return (
    <Card className="col-span-3">
      <CardHeader>
        <CardTitle>Property Listings Count</CardTitle>
      </CardHeader>
      <CardContent className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{
              top: 10,
              right: 30,
              left: 20,
              bottom: 70,
            }}
            onClick={(_, __, e) => {
              if (e && e.activePayload && e.activePayload[0]) {
                handleBarClick(e.activePayload[0].payload, e.activeTooltipIndex);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" angle={-45} textAnchor="end" height={70} interval={0} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar
              dataKey="count"
              name="New Listings"
              radius={[4, 4, 0, 0]}
              cursor="pointer"
              style={{ opacity: 0.8 }}
              onClick={(data, index) => handleBarClick(data, index)}
              fill={(entry, index) => (index === activeIndex ? "#4f46e5" : "#8884d8")}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
