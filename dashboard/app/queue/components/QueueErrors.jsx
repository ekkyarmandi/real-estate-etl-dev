"use client";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ExternalLink, RefreshCcw } from "lucide-react";
import { toast } from "react-toastify";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

export function QueueErrors() {
  const [queueErrors, setQueueErrors] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isUpdating, setIsUpdating] = useState(false);
  const [selectedActions, setSelectedActions] = useState({});
  const [urlTitles, setUrlTitles] = useState({});
  const [loadingTitles, setLoadingTitles] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [domains, setDomains] = useState([]);
  const [selectedDomain, setSelectedDomain] = useState("All");
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState("Error");
  const [isLoadingDomains, setIsLoadingDomains] = useState(true);
  const [totalResults, setTotalResults] = useState(0);
  const [isLoadingTitles, setIsLoadingTitles] = useState(false);

  // Fetch available domains
  const fetchDomains = async () => {
    try {
      const response = await fetch("http://localhost:8000/queue/domains");
      const data = await response.json();
      setDomains(data.domains);
    } catch (error) {
      console.error("Error fetching domains:", error);
      toast.error("Failed to load domains");
    } finally {
      setIsLoadingDomains(false);
    }
  };

  // Handle selection change for an item
  const handleSelectionChange = (queueId, status) => {
    setSelectedActions((prev) => ({
      ...prev,
      [queueId]: status,
    }));
  };

  // Process bulk updates
  const processBulkUpdates = async (singleItemId = null) => {
    // If singleItemId is provided, only process that item
    let updates;
    if (singleItemId) {
      const status = selectedActions[singleItemId];
      if (!status || status === "None") {
        toast.info("Please select a status first");
        return;
      }
      updates = [[singleItemId, status]];
    } else {
      updates = Object.entries(selectedActions).filter(([_, status]) => status !== "None");

      if (updates.length === 0) {
        toast.info("No items selected for update");
        return;
      }
    }

    setIsUpdating(true);

    // Show loading toast
    const loadingToastId = toast.loading(singleItemId ? "Updating item..." : `Updating ${updates.length} items...`);

    try {
      // Format data according to expected API format
      const items = updates.map(([id, status]) => ({
        id: parseInt(id),
        status,
      }));

      console.log("Sending update request with items:", items);

      // Send a single request with all updates
      const response = await fetch(`http://localhost:8000/queue/errors/bulk`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ items }),
      });

      if (!response.ok) {
        throw new Error(`Failed to process bulk update. Status: ${response.status}`);
      }

      // Get the response data
      const data = await response.json();
      console.log("Response from server:", data);

      // Check if response is in the expected format
      if (data.status === "success" && data.results) {
        // Handle successful updates
        const successfulIds = data.results.success || [];
        const failedIds = data.results.failed || [];

        if (successfulIds.length > 0) {
          // Convert IDs to strings for comparison
          const successIdSet = new Set(successfulIds.map((id) => id.toString()));

          // Remove the updated items from the state
          setQueueErrors((prevErrors) => {
            const filtered = prevErrors.filter((error) => !successIdSet.has(error.id.toString()));
            return filtered;
          });

          // Clear selections for updated items
          setSelectedActions((prev) => {
            const newState = { ...prev };
            successIdSet.forEach((id) => delete newState[id]);
            return newState;
          });

          // Show success message
          toast.update(loadingToastId, {
            render: `Successfully updated ${successfulIds.length} item${successfulIds.length !== 1 ? "s" : ""}`,
            type: "success",
            isLoading: false,
            autoClose: 3000,
          });
        } else {
          // No items were updated successfully
          toast.update(loadingToastId, {
            render: "No items were updated successfully",
            type: "info",
            isLoading: false,
            autoClose: 3000,
          });
        }

        // Show error message if there were failures
        if (failedIds.length > 0) {
          toast.error(`Failed to update ${failedIds.length} item${failedIds.length !== 1 ? "s" : ""}`);
        }
      } else {
        // Fallback if response is not in expected format
        console.log("Unexpected response format, using sent items");

        // Use the items we sent to update the UI
        const updatedIds = new Set(items.map((item) => item.id.toString()));

        setQueueErrors((prevErrors) => {
          const filtered = prevErrors.filter((error) => !updatedIds.has(error.id.toString()));
          return filtered;
        });

        // Clear selections for updated items
        setSelectedActions((prev) => {
          const newState = { ...prev };
          updatedIds.forEach((id) => delete newState[id]);
          return newState;
        });

        // Display message from response or fallback
        const message = data.message || `Updated ${updatedIds.size} items`;
        toast.update(loadingToastId, {
          render: message,
          type: "success",
          isLoading: false,
          autoClose: 3000,
        });
      }
    } catch (error) {
      console.error("Error processing bulk updates:", error);

      // Update the loading toast to error
      toast.update(loadingToastId, {
        render: error.message || "An error occurred while processing updates",
        type: "error",
        isLoading: false,
        autoClose: 3000,
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const fetchUrlTitle = async (url, id) => {
    try {
      const response = await fetch(`/api/proxy?url=${encodeURIComponent(url)}`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      const html = await response.text();
      const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
      const title = titleMatch ? titleMatch[1].trim() : "No title found";
      return {
        id,
        title,
        status: "success",
      };
    } catch (error) {
      return {
        id,
        title: error.message || "Failed to load URL",
        status: "error",
      };
    }
  };

  const fetchQueueErrors = async () => {
    try {
      setIsLoading(true);

      // Construct URL with filters
      let url = `http://localhost:8000/queue?page=${page}`;

      // Add status filter
      if (selectedStatus !== "All") {
        url += `&status=${selectedStatus}`;
      }

      // Add domain filter if selected
      if (selectedDomain !== "All") {
        url += `&domain=${selectedDomain}`;
      }

      // Add date filter if selected
      if (selectedDate) {
        const formattedDate = format(selectedDate, "yyyy-MM-dd");
        url += `&date=${formattedDate}`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error("Failed to fetch queue data");
      }

      const data = await response.json();
      setQueueErrors(data.results.items || []);
      setTotalPages(Math.ceil(data.results.total / data.results.count));
      setTotalResults(data.results.total || 0);

      // Initialize all selections to "None"
      const initialSelections = {};
      (data.results.items || []).forEach((error) => {
        initialSelections[error.id] = "None";
      });
      setSelectedActions(initialSelections);
    } catch (error) {
      console.error("Error fetching queue data:", error);
      toast.error(error.message || "Failed to load queue data");
    } finally {
      setIsLoading(false);
    }
  };

  // Apply filters and reload data
  const applyFilters = () => {
    setPage(1); // Reset to first page when filters change
    fetchQueueErrors();
  };

  const fetchAllTitles = async () => {
    if (isLoadingTitles) return;

    const unloadedItems = queueErrors.filter((error) => !urlTitles[error.id]);

    if (unloadedItems.length === 0) {
      toast.info("All titles are already loaded");
      return;
    }

    setIsLoadingTitles(true);
    const loadingToastId = toast.loading(`Loading ${unloadedItems.length} titles...`);

    try {
      // Process URLs in batches of 5
      const batchSize = 5;

      for (let i = 0; i < unloadedItems.length; i += batchSize) {
        const batch = unloadedItems.slice(i, i + batchSize);
        const promises = batch.map((error) => fetchUrlTitle(error.url, error.id));

        const batchResults = await Promise.all(promises);

        // Update titles for this batch
        const newTitles = {};
        batchResults.forEach((result) => {
          newTitles[result.id] = {
            title: result.title,
            status: result.status,
          };
        });

        // Update state with new titles
        setUrlTitles((prev) => ({
          ...prev,
          ...newTitles,
        }));

        // Update progress
        const progress = Math.min(i + batchSize, unloadedItems.length);
        toast.update(loadingToastId, {
          render: `Loading titles... (${progress}/${unloadedItems.length})`,
        });
      }

      toast.update(loadingToastId, {
        render: `Successfully loaded ${unloadedItems.length} titles`,
        type: "success",
        isLoading: false,
        autoClose: 3000,
      });
    } catch (error) {
      toast.update(loadingToastId, {
        render: "Failed to load some titles",
        type: "error",
        isLoading: false,
        autoClose: 3000,
      });
    } finally {
      setIsLoadingTitles(false);
    }
  };

  useEffect(() => {
    fetchDomains();
  }, []);

  useEffect(() => {
    fetchQueueErrors();
  }, [page]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Queue List</CardTitle>
          <CardDescription>URL entries from the queue</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4 w-fit border p-4 rounded-md items-end mb-4">
          <div>
            <label className="text-sm font-medium" htmlFor="domain">
              Domain
            </label>
            <Select value={selectedDomain} onValueChange={setSelectedDomain} disabled={isLoadingDomains}>
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
            <Select value={selectedStatus} onValueChange={setSelectedStatus} disabled={isLoading}>
              <SelectTrigger className="w-[180px] hover:cursor-pointer">
                <SelectValue placeholder="Select a status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="All">All</SelectItem>
                <SelectItem value="Available">Available</SelectItem>
                <SelectItem value="Delisted">Delisted</SelectItem>
                <SelectItem value="Sold">Sold</SelectItem>
                <SelectItem value="Error">Error</SelectItem>
                <SelectItem value="Rented">Rented</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col">
            <label className="text-sm font-medium" htmlFor="date">
              Date
            </label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className={cn("w-[180px] justify-start text-left font-normal hover:cursor-pointer", !selectedDate && "text-muted-foreground")}>
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedDate ? format(selectedDate, "PPP") : "Select date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar mode="single" selected={selectedDate} onSelect={setSelectedDate} initialFocus />
              </PopoverContent>
            </Popover>
          </div>
          <div>
            <Button className="hover:cursor-pointer" onClick={applyFilters} disabled={isLoading}>
              Apply Filters
            </Button>
          </div>
          <div>
            <Button
              variant="outline"
              onClick={() => {
                setSelectedDomain("All");
                setSelectedDate(null);
                setSelectedStatus("Error");
                setPage(1);
                fetchQueueErrors();
              }}
              disabled={isLoading}
              className="hover:cursor-pointer"
            >
              Reset
            </Button>
          </div>
        </div>

        <div className="flex justify-end mb-4 gap-2">
          <Button variant="outline" size="sm" onClick={fetchAllTitles} disabled={isLoading || isLoadingTitles} className="flex items-center gap-2">
            <span>{isLoadingTitles ? "Loading Titles..." : "Fetch All"}</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              fetchQueueErrors();
            }}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <span>Reload</span>
            <RefreshCcw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardContent>
      <CardContent>
        <div className="rounded-md border">
          <div className="px-4 py-2">
            <p className="text-sm font-light">Total results: {totalResults}</p>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>URL</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {queueErrors.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={2} className="text-center py-6 text-muted-foreground">
                    No errors found
                  </TableCell>
                </TableRow>
              ) : (
                queueErrors.map((error) => (
                  <TableRow key={error.id}>
                    <TableCell className="font-medium">
                      <div className="flex gap-2">
                        <a href={error.url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-4 w-4 inline-block mr-2" />
                          {error.url.length > 50 ? error.url.substring(0, 50) + "..." : error.url}
                        </a>
                      </div>
                      {urlTitles[error.id] && <span className={`text-xs block mt-1 ${urlTitles[error.id].status === "success" ? "text-muted-foreground" : "text-red-500"}`}>{urlTitles[error.id].title}</span>}
                      {loadingTitles[error.id] && <span className="text-xs block mt-1 text-muted-foreground">Loading...</span>}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2 items-center">
                        <RadioGroup
                          defaultValue="None"
                          value={selectedActions[error.id]}
                          onValueChange={async (value) => {
                            try {
                              // Optimistic update
                              setSelectedActions((prev) => ({
                                ...prev,
                                [error.id]: value,
                              }));
                              // Actual API call
                              await handleSelectionChange(error.id, value);
                            } catch (error) {
                              // Revert on error
                              setSelectedActions((prev) => ({
                                ...prev,
                                [error.id]: prev[error.id],
                              }));
                            }
                          }}
                          disabled={isUpdating}
                          className="flex gap-4"
                        >
                          <div className="flex items-center space-x-2">
                            <RadioGroupItem value="None" id={`none-${error.id}`} />
                            <Label htmlFor={`none-${error.id}`}>Select status...</Label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <RadioGroupItem value="Available" id={`available-${error.id}`} />
                            <Label htmlFor={`available-${error.id}`}>Available</Label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <RadioGroupItem value="Delisted" id={`delisted-${error.id}`} />
                            <Label htmlFor={`delisted-${error.id}`}>Delisted</Label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <RadioGroupItem value="Sold" id={`sold-${error.id}`} />
                            <Label htmlFor={`sold-${error.id}`}>Sold</Label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <RadioGroupItem value="Rented" id={`rented-${error.id}`} />
                            <Label htmlFor={`rented-${error.id}`}>Rented</Label>
                          </div>
                        </RadioGroup>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex items-center justify-end space-x-2 py-4">
          <Button variant="outline" size="sm" onClick={() => setPage((prev) => Math.max(prev - 1, 1))} disabled={page === 1 || isUpdating}>
            Previous
          </Button>
          <div className="text-sm">
            Page {page} of {totalPages}
          </div>
          <Button variant="outline" size="sm" onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))} disabled={page === totalPages || isUpdating}>
            Next
          </Button>
        </div>

        {/* Floating action button with selection counter */}
        {Object.values(selectedActions).some((v) => v !== "None") && (
          <div className="fixed bottom-8 right-1/2 translate-x-[50%] z-50">
            <div className="flex items-center gap-2 bg-background shadow-lg rounded-full px-4 py-2 border">
              <div className="rounded-lg border h-8 w-8 flex items-center justify-center font-medium">{Object.values(selectedActions).filter((v) => v !== "None").length}</div>
              <Button onClick={() => processBulkUpdates()} disabled={isUpdating} className={`${!isUpdating ? "cursor-pointer" : "cursor-not-allowed"}`} size="sm">
                {isUpdating ? "Updating..." : "Process Selected"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
