"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon, ExternalLink, Check, X, Loader2 } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

export default function TagsPage() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const tagsEndpoint = `${baseUrl}/tags`;

  const [date, setDate] = useState();
  const [tags, setTags] = useState([]);
  const [selectedTag, setSelectedTag] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTagDetailsLoading, setIsTagDetailsLoading] = useState(false);
  const [tagDetails, setTagDetails] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Add new state for edited properties
  const [editedProperties, setEditedProperties] = useState({});

  // Add new state for cells being edited
  const [editingCells, setEditingCells] = useState({});

  // Add loading state for specific rows
  const [savingRows, setSavingRows] = useState({});

  // Toggle edit mode for a cell
  const toggleEditMode = useCallback((propertyId, field) => {
    setEditingCells((prev) => {
      const key = `${propertyId}-${field}`;
      const newState = { ...prev };

      // If already editing this cell, cancel editing
      if (newState[key]) {
        delete newState[key];
      } else {
        // Start editing this cell
        newState[key] = true;
      }

      return newState;
    });
  }, []);

  // Check if a cell is in edit mode
  const isEditing = useCallback(
    (propertyId, field) => {
      const key = `${propertyId}-${field}`;
      return !!editingCells[key];
    },
    [editingCells]
  );

  // Fetch tag details
  const fetchTagDetails = useCallback(
    async (page = 1) => {
      if (!selectedTag) return;

      setIsTagDetailsLoading(true);

      try {
        // Build URL with tag ID, date filter, and pagination
        let url = `${tagsEndpoint}/${selectedTag.id}`;

        // Create URL parameters
        const params = new URLSearchParams();

        // Add date if available
        if (date) {
          params.append("date", format(date, "yyyy-MM-dd"));
        }

        // Add pagination
        params.append("page", page.toString());

        // Append parameters to URL
        url += `?${params.toString()}`;

        console.log("Fetching tag details from:", url);

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Error ${response.status}: Failed to fetch tag details`);
        }

        const data = await response.json();
        console.log("Tag details data:", data);

        setTagDetails(data.data || []);
        setTotalResults(data.total || 0);
        setCurrentPage(page);

        // Calculate total pages
        const pageSize = data.size || 50;
        const total = data.total || 0;
        setTotalPages(Math.ceil(total / pageSize));
      } catch (error) {
        console.error("Error fetching tag details:", error);
        toast.error(`Failed to load tag details: ${error.message}`);
        setTagDetails([]);
        setTotalResults(0);
      } finally {
        setIsTagDetailsLoading(false);
      }
    },
    [selectedTag, date, tagsEndpoint]
  );

  // Fetch tags list with optional date filter
  const fetchTagsList = useCallback(async () => {
    setIsLoading(true);
    try {
      // Construct URL with date parameter if available
      let url = tagsEndpoint;
      if (date) {
        const formattedDate = format(date, "yyyy-MM-dd");
        url += `?date=${formattedDate}`;
      }

      console.log("Fetching tags list from:", url);

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: Failed to fetch tags`);
      }
      const data = await response.json();
      setTags(data.tags || []);
    } catch (error) {
      console.error("Error fetching tags:", error);
      toast.error("Failed to load tags");
      setTags([]);
    } finally {
      setIsLoading(false);
    }
  }, [tagsEndpoint, date]);

  // Handle date change
  const handleDateChange = useCallback((newDate) => {
    setDate(newDate);
    // Reset selected tag when date changes
    setSelectedTag(null);
    setTagDetails([]);
    setTotalResults(0);
    setTotalPages(1);
  }, []);

  // Load tags on initial mount and when date changes
  useEffect(() => {
    fetchTagsList();
  }, [fetchTagsList]);

  // Fetch tag details when tag selection changes
  useEffect(() => {
    if (selectedTag) {
      fetchTagDetails(1);
    }
  }, [selectedTag, fetchTagDetails]);

  // Handle tag selection
  const handleTagClick = useCallback(
    (tag) => {
      if (selectedTag && selectedTag.id === tag.id) {
        setSelectedTag(null);
        setTagDetails([]);
        setTotalResults(0);
      } else {
        setSelectedTag(tag);
      }
    },
    [selectedTag]
  );

  // Handle page change
  const handlePageChange = useCallback(
    (newPage) => {
      if (newPage >= 1 && newPage <= totalPages) {
        fetchTagDetails(newPage);
      }
    },
    [fetchTagDetails, totalPages]
  );

  // Handle property field change
  const handlePropertyChange = useCallback((propertyId, field, value) => {
    setEditedProperties((prev) => ({
      ...prev,
      [propertyId]: {
        ...(prev[propertyId] || {}),
        [field]: value,
      },
    }));
  }, []);

  // Get value for a property field, with edited value taking precedence
  const getPropertyValue = useCallback(
    (property, field) => {
      if (editedProperties[property.id] && editedProperties[property.id][field] !== undefined) {
        return editedProperties[property.id][field];
      }
      return property[field];
    },
    [editedProperties]
  );

  // Handle cell value change and immediate update
  const handleCellChange = useCallback((propertyId, field, value) => {
    // Update the edited properties state
    setEditedProperties((prev) => ({
      ...prev,
      [propertyId]: {
        ...(prev[propertyId] || {}),
        [field]: value,
      },
    }));

    // Update the tagDetails to immediately reflect the change in the UI
    setTagDetails((prevDetails) => prevDetails.map((property) => (property.id === propertyId ? { ...property, [field]: value } : property)));
  }, []);

  // Handle solving or ignoring an issue
  const handleMarkIssue = useCallback(
    async (propertyId, tagName, mode) => {
      setSavingRows((prev) => ({ ...prev, [propertyId]: true }));

      try {
        // The API expects query parameters, not JSON body
        const url = new URL(`${baseUrl}/tags/${propertyId}/mark-as-solved`);
        url.searchParams.append("tag", tagName);
        url.searchParams.append("mode", mode);

        console.log("Making request to:", url.toString());

        const response = await fetch(url.toString(), {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(`Error ${response.status}: ${errorData.detail || `Failed to mark issue as ${mode}`}`);
        }

        const result = await response.json();
        toast.success(result.message || `Issue marked as ${mode} successfully`);

        // Update the UI without triggering a full refresh
        // Remove the property from the current display
        setTagDetails((prevDetails) => prevDetails.filter((p) => p.id !== propertyId));

        // Update the tag count in the tag list
        if (selectedTag) {
          setTags((prevTags) => prevTags.map((tag) => (tag.id === selectedTag.id ? { ...tag, count: Math.max(0, tag.count - 1) } : tag)));

          // Update total results
          setTotalResults((prev) => Math.max(0, prev - 1));
        }
      } catch (error) {
        console.error(`Error marking issue as ${mode}:`, error);
        toast.error(`Failed to mark issue as ${mode}: ${error.message}`);
      } finally {
        setSavingRows((prev) => {
          const newState = { ...prev };
          delete newState[propertyId];
          return newState;
        });
      }
    },
    [baseUrl, selectedTag]
  );

  // Handle solving issue - convenience wrapper for handleMarkIssue with mode=solved
  const handleSolveIssue = useCallback(
    (propertyId, tagName) => {
      handleMarkIssue(propertyId, tagName, "solved");
    },
    [handleMarkIssue]
  );

  // Handle ignoring issue - convenience wrapper for handleMarkIssue with mode=ignored
  const handleIgnoreIssue = useCallback(
    (propertyId, tagName) => {
      handleMarkIssue(propertyId, tagName, "ignored");
    },
    [handleMarkIssue]
  );

  // Handle save button click
  const handleSave = useCallback(
    async (propertyId) => {
      if (!editedProperties[propertyId]) return;

      setSavingRows((prev) => ({ ...prev, [propertyId]: true }));

      try {
        // Send PUT request to update the property
        const response = await fetch(`${baseUrl}/tags/${propertyId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(editedProperties[propertyId]),
        });

        if (!response.ok) {
          throw new Error(`Error ${response.status}: Failed to update property`);
        }

        const result = await response.json();
        toast.success(result.message || "Property updated successfully");

        // The changes are already applied to the UI through handleCellChange
        // Clear edited properties for this property
        setEditedProperties((prev) => {
          const newState = { ...prev };
          delete newState[propertyId];
          return newState;
        });

        // Clear editing cells
        setEditingCells({});

        // No need to refresh data as we've already updated the UI
        // This prevents the fetchTagsList from being triggered
      } catch (error) {
        console.error("Error updating property:", error);
        toast.error(`Failed to update property: ${error.message}`);
      } finally {
        setSavingRows((prev) => {
          const newState = { ...prev };
          delete newState[propertyId];
          return newState;
        });
      }
    },
    [editedProperties, baseUrl]
  );

  // Determine if a property has unsaved changes
  const hasChanges = useCallback(
    (propertyId) => {
      return !!editedProperties[propertyId];
    },
    [editedProperties]
  );

  // Add handleBulkMarked function to bulk mark issues as solved or ignored
  const handleBulkMarked = useCallback(
    async (tagName, mode) => {
      if (!tagName || !tagDetails.length) return;

      // Show loading state for all rows
      const propertyIds = tagDetails.map((p) => p.id);
      setSavingRows(propertyIds.reduce((acc, id) => ({ ...acc, [id]: true }), {}));

      try {
        // Build the request payload
        const payload = {
          property_ids: propertyIds,
          mode: mode, // "solved" or "ignored"
        };

        console.log(`Bulk marking ${propertyIds.length} properties as ${mode}`);

        // Send the request
        const response = await fetch(`${baseUrl}/tags/bulk-marked/${tagName}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(`Error ${response.status}: ${errorData.detail || `Failed to mark issues as ${mode}`}`);
        }

        const result = await response.json();
        toast.success(result.message || `${propertyIds.length} issues marked as ${mode} successfully`);

        // Update the UI
        // 1. Clear the current list
        setTagDetails([]);
        // 2. Decrement the count in the tag list by the number of items processed
        if (selectedTag) {
          setTags((prevTags) => prevTags.map((tag) => (tag.id === selectedTag.id ? { ...tag, count: Math.max(0, tag.count - propertyIds.length) } : tag)));
          // 3. Update total results
          setTotalResults(0);
        }
      } catch (error) {
        console.error(`Error bulk marking issues as ${mode}:`, error);
        toast.error(`Failed to mark issues as ${mode}: ${error.message}`);
      } finally {
        // Clear all loading states
        setSavingRows({});
      }
    },
    [baseUrl, selectedTag, tagDetails]
  );

  // Handle bulk solve - convenience wrapper for handleBulkMarked with mode=solved
  const handleSolveAll = useCallback(
    (tagName) => {
      handleBulkMarked(tagName, "solved");
    },
    [handleBulkMarked]
  );

  // Handle bulk ignore - convenience wrapper for handleBulkMarked with mode=ignored
  const handleIgnoreAll = useCallback(
    (tagName) => {
      handleBulkMarked(tagName, "ignored");
    },
    [handleBulkMarked]
  );

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-2xl font-bold mb-6 md:mb-8">Data Quality Control</h1>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 p-4 border rounded-md">
          <div>
            <p className="text-md font-medium mb-2">Filter by Date</p>
            <div className="flex gap-2 items-center">
              <DatePicker date={date} setDate={handleDateChange} />
            </div>
          </div>
          <div>
            <p className="text-md font-medium mb-2">Tags</p>
            <div className="flex gap-2 flex-wrap">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : tags.length > 0 ? (
                tags.map((tag) => (
                  <Badge key={tag.id} className="hover:bg-muted cursor-pointer" variant={selectedTag && selectedTag.id === tag.id ? "default" : "outline"} onClick={() => handleTagClick(tag)}>
                    {tag.name} ({tag.count})
                  </Badge>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No tags found</p>
              )}
            </div>
          </div>
        </div>

        {selectedTag && (
          <div className="flex flex-col gap-4 p-4 border rounded-md">
            <h3 className="text-lg font-medium">Properties with {selectedTag.name} issue</h3>

            {isTagDetailsLoading ? (
              <div className="py-8 text-center">
                <p className="text-muted-foreground animate-pulse">Loading properties...</p>
              </div>
            ) : tagDetails.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-muted-foreground">No properties found with this issue.</p>
              </div>
            ) : (
              <>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="text-xs">
                        <TableHead className="whitespace-nowrap">Source</TableHead>
                        <TableHead className="whitespace-nowrap">Title</TableHead>
                        <TableHead className="whitespace-nowrap">Description</TableHead>
                        <TableHead className="whitespace-nowrap">Region</TableHead>
                        <TableHead className="whitespace-nowrap">Location</TableHead>
                        <TableHead className="whitespace-nowrap">Leasehold Years</TableHead>
                        <TableHead className="whitespace-nowrap">Contract Type</TableHead>
                        <TableHead className="whitespace-nowrap">Property Type</TableHead>
                        <TableHead className="whitespace-nowrap">Bedrooms</TableHead>
                        <TableHead className="whitespace-nowrap">Bathrooms</TableHead>
                        <TableHead className="whitespace-nowrap">Build Size</TableHead>
                        <TableHead className="whitespace-nowrap">Price</TableHead>
                        <TableHead className="whitespace-nowrap">Availability</TableHead>
                        <TableHead className="whitespace-nowrap">Sold At</TableHead>
                        <TableHead className="whitespace-nowrap">Excluded By</TableHead>
                        <TableHead className="whitespace-nowrap text-right">Actions</TableHead>
                        <TableHead className="whitespace-nowrap text-right">Issue</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs">
                      {tagDetails.map((property, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">
                            <a href={property.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center gap-1">
                              <span>{property.source}</span>
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </TableCell>
                          <TableCell className="max-w-[150px] truncate cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "title")}>
                            {isEditing(property.id, "title") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                value={getPropertyValue(property, "title") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "title", e.target.value);
                                  handlePropertyChange(property.id, "title", e.target.value);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "title")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "title");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.title || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "description")}>
                            {isEditing(property.id, "description") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                value={getPropertyValue(property, "description") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "description", e.target.value);
                                  handlePropertyChange(property.id, "description", e.target.value);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "description")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "description");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.description || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "region")}>
                            {isEditing(property.id, "region") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                value={getPropertyValue(property, "region") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "region", e.target.value);
                                  handlePropertyChange(property.id, "region", e.target.value);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "region")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "region");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.region || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "location")}>
                            {isEditing(property.id, "location") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                value={getPropertyValue(property, "location") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "location", e.target.value);
                                  handlePropertyChange(property.id, "location", e.target.value);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "location")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "location");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.location || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "leasehold_years")}>
                            {isEditing(property.id, "leasehold_years") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                type="number"
                                value={getPropertyValue(property, "leasehold_years") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "leasehold_years", parseFloat(e.target.value) || null);
                                  handlePropertyChange(property.id, "leasehold_years", parseFloat(e.target.value) || null);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "leasehold_years")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "leasehold_years");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.leasehold_years || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "contract_type")}>
                            {isEditing(property.id, "contract_type") ? (
                              <Select
                                value={getPropertyValue(property, "contract_type") || ""}
                                onValueChange={(value) => {
                                  handleCellChange(property.id, "contract_type", value);
                                  handlePropertyChange(property.id, "contract_type", value);
                                }}
                                open={true}
                              >
                                <SelectTrigger className="h-7 text-xs w-full">
                                  <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="Freehold">Freehold</SelectItem>
                                  <SelectItem value="Leasehold">Leasehold</SelectItem>
                                  <SelectItem value="Rental">Rental</SelectItem>
                                </SelectContent>
                              </Select>
                            ) : (
                              <span>{property.contract_type || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "property_type")}>
                            {isEditing(property.id, "property_type") ? (
                              <Select
                                value={getPropertyValue(property, "property_type") || ""}
                                onValueChange={(value) => {
                                  handleCellChange(property.id, "property_type", value);
                                  handlePropertyChange(property.id, "property_type", value);
                                }}
                                open={true}
                              >
                                <SelectTrigger className="h-7 text-xs w-full">
                                  <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="Villa">Villa</SelectItem>
                                  <SelectItem value="House">House</SelectItem>
                                  <SelectItem value="Land">Land</SelectItem>
                                  <SelectItem value="Apartment">Apartment</SelectItem>
                                  <SelectItem value="Hotel">Hotel</SelectItem>
                                  <SelectItem value="Townhouse">Townhouse</SelectItem>
                                  <SelectItem value="Commercial">Commercial</SelectItem>
                                  <SelectItem value="Loft">Loft</SelectItem>
                                </SelectContent>
                              </Select>
                            ) : (
                              <span>{property.property_type || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "bedrooms")}>
                            {isEditing(property.id, "bedrooms") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                type="number"
                                value={getPropertyValue(property, "bedrooms") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "bedrooms", parseFloat(e.target.value) || null);
                                  handlePropertyChange(property.id, "bedrooms", parseFloat(e.target.value) || null);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "bedrooms")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "bedrooms");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.bedrooms || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "bathrooms")}>
                            {isEditing(property.id, "bathrooms") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                type="number"
                                value={getPropertyValue(property, "bathrooms") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "bathrooms", parseFloat(e.target.value) || null);
                                  handlePropertyChange(property.id, "bathrooms", parseFloat(e.target.value) || null);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "bathrooms")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "bathrooms");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.bathrooms || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "build_size")}>
                            {isEditing(property.id, "build_size") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                type="number"
                                value={getPropertyValue(property, "build_size") || ""}
                                onChange={(e) => {
                                  handleCellChange(property.id, "build_size", parseFloat(e.target.value) || null);
                                  handlePropertyChange(property.id, "build_size", parseFloat(e.target.value) || null);
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "build_size")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "build_size");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.build_size || "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "price")}>
                            {isEditing(property.id, "price") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                value={`${getPropertyValue(property, "currency") || property.currency} ${getPropertyValue(property, "price") || property.price}`.trim()}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  // Parse the price input to extract currency and value
                                  const parts = value.split(" ");
                                  if (parts.length >= 2) {
                                    const currency = parts[0];
                                    // Join the rest and remove any commas or non-numeric chars except decimal point
                                    const priceText = parts
                                      .slice(1)
                                      .join("")
                                      .replace(/[^\d.]/g, "");
                                    const price = priceText ? parseFloat(priceText) : null;

                                    // Update the price and currency separately
                                    handleCellChange(property.id, "price", price);
                                    handlePropertyChange(property.id, "price", price);

                                    handleCellChange(property.id, "currency", currency);
                                    handlePropertyChange(property.id, "currency", currency);
                                  }
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "price")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "price");
                                  }
                                }}
                              />
                            ) : (
                              <span>{property.price ? `${property.currency} ${Number(property.price).toLocaleString()}` : "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "availability")}>
                            {isEditing(property.id, "availability") ? (
                              <Select
                                value={getPropertyValue(property, "availability") || "Available"}
                                onValueChange={(value) => {
                                  handleCellChange(property.id, "availability", value);
                                  handlePropertyChange(property.id, "availability", value);
                                }}
                                open={true}
                              >
                                <SelectTrigger className="h-7 text-xs w-full">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="Available">Available</SelectItem>
                                  <SelectItem value="Sold">Sold</SelectItem>
                                  <SelectItem value="Delisted">Delisted</SelectItem>
                                </SelectContent>
                              </Select>
                            ) : (
                              <Badge variant={property.is_available ? "success" : "destructive"}>{property.availability || (property.is_available ? "Available" : "Not Available")}</Badge>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "sold_at")}>
                            {isEditing(property.id, "sold_at") ? (
                              <Popover open={true} onOpenChange={() => toggleEditMode(property.id, "sold_at")}>
                                <PopoverTrigger asChild>
                                  <Button variant={"outline"} className="h-7 w-full text-xs justify-start font-normal">
                                    {getPropertyValue(property, "sold_at") ? new Date(getPropertyValue(property, "sold_at")).toLocaleDateString() : "Not sold"}
                                  </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto p-0" align="start">
                                  <Calendar
                                    mode="single"
                                    selected={getPropertyValue(property, "sold_at") ? new Date(getPropertyValue(property, "sold_at")) : undefined}
                                    onSelect={(date) => {
                                      handleCellChange(property.id, "sold_at", date?.toISOString() || null);
                                      handlePropertyChange(property.id, "sold_at", date?.toISOString() || null);
                                    }}
                                    initialFocus
                                  />
                                </PopoverContent>
                              </Popover>
                            ) : (
                              <span>{property.sold_at ? new Date(property.sold_at).toLocaleDateString() : "-"}</span>
                            )}
                          </TableCell>
                          <TableCell className="cursor-pointer hover:bg-muted/50" onClick={() => toggleEditMode(property.id, "excluded_by")}>
                            {isEditing(property.id, "excluded_by") ? (
                              <Input
                                className="h-7 text-xs w-full"
                                value={getPropertyValue(property, "excluded_by") || ""}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  handleCellChange(property.id, "excluded_by", value);
                                  handlePropertyChange(property.id, "excluded_by", value);

                                  // The backend will handle setting is_excluded based on excluded_by
                                }}
                                autoFocus
                                onBlur={() => toggleEditMode(property.id, "excluded_by")}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    toggleEditMode(property.id, "excluded_by");
                                  }
                                }}
                              />
                            ) : (
                              <div>{property.excluded_by ? <span>{property.excluded_by}</span> : "-"}</div>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end space-x-1">
                              {hasChanges(property.id) ? (
                                <>
                                  {savingRows[property.id] ? (
                                    <Button size="sm" variant="outline" className="h-7 w-7 p-0" disabled>
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    </Button>
                                  ) : (
                                    <>
                                      <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => handleSave(property.id)}>
                                        <Check className="h-3 w-3" />
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 w-7 p-0"
                                        onClick={() => {
                                          // Revert changes in UI
                                          setTagDetails((prevDetails) => [...prevDetails]);
                                          // Clear edited properties
                                          setEditedProperties((prev) => {
                                            const newState = { ...prev };
                                            delete newState[property.id];
                                            return newState;
                                          });
                                        }}
                                      >
                                        <X className="h-3 w-3" />
                                      </Button>
                                    </>
                                  )}
                                </>
                              ) : (
                                <Button size="sm" variant="outline" className="h-7" disabled>
                                  No changes
                                </Button>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end space-x-1">
                              {savingRows[property.id] ? (
                                <>
                                  <Button size="sm" className="bg-emerald-500 hover:bg-emerald-600 h-7" disabled>
                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                    Processing...
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button size="sm" className="bg-emerald-500 hover:bg-emerald-600 h-7" onClick={() => handleSolveIssue(property.id, selectedTag?.id)}>
                                    Solve
                                  </Button>
                                  <Button size="sm" variant="outline" className="h-7" onClick={() => handleIgnoreIssue(property.id, selectedTag?.id)}>
                                    Ignore
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {tagDetails.length} of {totalResults} results
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      className="bg-emerald-500 hover:bg-emerald-600"
                      variant="default"
                      size="sm"
                      onClick={() => handleSolveAll(selectedTag?.id)}
                      disabled={isTagDetailsLoading || tagDetails.length === 0 || Object.keys(savingRows).length > 0}
                    >
                      {Object.keys(savingRows).length > 0 ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        "Solve All"
                      )}
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleIgnoreAll(selectedTag?.id)} disabled={isTagDetailsLoading || tagDetails.length === 0 || Object.keys(savingRows).length > 0}>
                      {Object.keys(savingRows).length > 0 ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        "Ignore All"
                      )}
                    </Button>
                    {totalPages > 1 && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1 || isTagDetailsLoading}>
                          Previous
                        </Button>
                        <div className="text-sm">
                          Page {currentPage} of {totalPages}
                        </div>
                        <Button variant="outline" size="sm" onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages || isTagDetailsLoading}>
                          Next
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function DatePicker({ date, setDate }) {
  return (
    <div className="flex items-center gap-2">
      <Popover>
        <PopoverTrigger asChild>
          <Button variant={"outline"} className={cn("w-[230px] justify-start text-left font-normal", !date && "text-muted-foreground")}>
            <CalendarIcon className="mr-2 size-4" />
            {date ? format(date, "PPP") : <span>Pick a date</span>}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar mode="single" selected={date} onSelect={setDate} disabled={(date) => date > new Date() || date < new Date("2024-01-01")} initialFocus />
        </PopoverContent>
      </Popover>

      {date && (
        <Button variant="ghost" size="icon" onClick={() => setDate(undefined)} className="rounded-full h-8 w-8" title="Clear date filter">
          <span className="sr-only">Clear date</span>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-x">
            <path d="M18 6 6 18"></path>
            <path d="m6 6 12 12"></path>
          </svg>
        </Button>
      )}
    </div>
  );
}
