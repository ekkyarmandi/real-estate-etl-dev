"use client";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ExternalLink, RefreshCcw } from "lucide-react";
import { toast } from "react-toastify";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

export function QueueErrors() {
  const [queueErrors, setQueueErrors] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isUpdating, setIsUpdating] = useState(false);
  const [selectedActions, setSelectedActions] = useState({});
  const [urlTitles, setUrlTitles] = useState({});
  const [loadingTitles, setLoadingTitles] = useState({});
  const [isLoading, setIsLoading] = useState(false);

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
    // Set loading state for this specific URL
    setLoadingTitles((prev) => ({ ...prev, [id]: true }));

    try {
      // Call our proxy API endpoint
      const response = await fetch(`/api/proxy?url=${encodeURIComponent(url)}`);

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }

      const html = await response.text();

      // Extract title using regex
      const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
      const title = titleMatch ? titleMatch[1].trim() : "No title found";

      // Store the title
      setUrlTitles((prev) => ({
        ...prev,
        [id]: {
          title,
          status: "success",
        },
      }));
    } catch (error) {
      console.error("Error fetching URL:", error);

      // Store the error
      setUrlTitles((prev) => ({
        ...prev,
        [id]: {
          title: error.message || "Failed to load URL",
          status: "error",
        },
      }));
    } finally {
      // Clear loading state
      setLoadingTitles((prev) => ({ ...prev, [id]: false }));
    }
  };

  const fetchQueueErrors = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`http://localhost:8000/queue/errors?page=${page}`);

      if (!response.ok) {
        throw new Error("Failed to fetch queue errors");
      }

      const data = await response.json();
      setQueueErrors(data.results.queues);
      setTotalPages(Math.ceil(data.results.total / data.results.count));

      // Initialize all selections to "None"
      const initialSelections = {};
      data.results.queues.forEach((error) => {
        initialSelections[error.id] = "None";
      });
      setSelectedActions(initialSelections);
    } catch (error) {
      console.error("Error fetching queue errors:", error);
      toast.error(error.message || "Failed to load queue errors");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQueueErrors();
  }, [page]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Queue Errors</CardTitle>
          <CardDescription>URLs with error status from queue</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(1); // Reset to first page
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
                        <button className="px-2 py-1 text-xs rounded-md border hover:cursor-pointer hover:bg-muted" onClick={() => fetchUrlTitle(error.url, error.id)} disabled={loadingTitles[error.id]}>
                          {loadingTitles[error.id] ? "Loading..." : "Load"}
                        </button>
                      </div>
                      {urlTitles[error.id] && <span className={`text-xs block mt-1 ${urlTitles[error.id].status === "success" ? "text-muted-foreground" : "text-red-500"}`}>{urlTitles[error.id].title}</span>}
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
