"use client";

import { useState } from "react";
import { ListingsChart } from "@/components/listings-chart";
import { ReportTable } from "@/components/report-table";

export default function Page() {
  const [selectedDate, setSelectedDate] = useState(null);

  const handleDateSelect = (date) => {
    setSelectedDate(date);
  };

  return (
    <>
      <div className="w-full">
        <ListingsChart onDateSelect={handleDateSelect} />
      </div>
      {selectedDate && <ReportTable selectedDate={selectedDate} />}
    </>
  );
}
