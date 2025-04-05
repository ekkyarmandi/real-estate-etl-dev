import { useState, useEffect } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

export function ManualCheck() {
  const [domains, setDomains] = useState([]);
  const [selectedDomain, setSelectedDomain] = useState("All");
  const [status, setStatus] = useState("All");
  const [date, setDate] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [queueUrl, setQueueUrl] = useState("");

  async function fetchDomains() {
    const response = await fetch("http://localhost:8000/queue/domains");
    const data = await response.json();
    setDomains(data.domains);
    setIsLoading(false);
  }

  useEffect(() => {
    fetchDomains();
  }, []);

  useEffect(() => {
    const formattedDate = date ? format(date, "yyyy-MM-dd") : "";
    const newUrl = `http://localhost:8000/queue?domain=${selectedDomain}&status=${status}${date ? `&date=${formattedDate}` : ""}`;
    setQueueUrl(newUrl);
  }, [selectedDomain, status, date]);

  return (
    <div>
      <div className="flex gap-4 w-fit border p-4 rounded-md items-end">
        <div>
          <label className="text-sm font-medium" htmlFor="domain">
            Domain
          </label>
          <Select value={selectedDomain} onValueChange={setSelectedDomain} disabled={isLoading}>
            <SelectTrigger className="w-[180px] hover:cursor-pointer">
              <SelectValue placeholder="Select a domain" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All</SelectItem>
              {domains.map((domain) => (
                <SelectItem key={domain} value={domain}>
                  {domain}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="status">
            Status
          </label>
          <Select value={status} onValueChange={setStatus} disabled={isLoading}>
            <SelectTrigger className="w-[180px] hover:cursor-pointer">
              <SelectValue placeholder="Select a status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All</SelectItem>
              <SelectItem value="Available">Available</SelectItem>
              <SelectItem value="Delisted">Delisted</SelectItem>
              <SelectItem value="Sold">Sold</SelectItem>
              <SelectItem value="Error">Error</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="date">
            Date
          </label>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className={cn("w-[180px] justify-start text-left font-normal hover:cursor-pointer", !date && "text-muted-foreground")}>
                <CalendarIcon className="mr-2 h-4 w-4" />
                {date ? format(date, "PPP") : "Select date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0">
              <Calendar mode="single" selected={date} onSelect={setDate} initialFocus />
            </PopoverContent>
          </Popover>
        </div>
        <div>
          <Button className="hover:cursor-pointer">Filter</Button>
        </div>
      </div>
      <p className="text-sm font-light">{queueUrl}</p>
    </div>
  );
}
