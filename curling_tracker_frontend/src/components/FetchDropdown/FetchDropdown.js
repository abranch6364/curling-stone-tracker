import React, { useState } from "react";

import { Portal, Select, Spinner, createListCollection } from "@chakra-ui/react"
import { useQuery } from '@tanstack/react-query';

const FetchDropdown = ({api_url, 
                        jsonToList, 
                        itemToKey, 
                        itemToString, 
                        label, 
                        placeholder, 
                        value,
                        setValue}) => {

  const [localValue, setLocalValue] = useState(null);
  const displayValue = value !== undefined ? value : localValue

  const localOnValueChange = (details) => {
    if (setValue !== undefined) {
      setValue(details.value[0]);
    } else {
      setLocalValue(details.value[0]);
    }
  };

  const fetchData = async () => {
    const response = await fetch(api_url);
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }
    return response.json();
  }

  const { data, error, isLoading } = useQuery({
                              queryKey: [api_url],
                              queryFn: () => fetchData(),
                              select: (data) => createListCollection({
                                              items: jsonToList(data),
                                              itemToString: itemToString,
                                              itemToValue: itemToKey,
                                              enable:true,
                                          }),
                          });
  
  if (error) {
      return <div>Error: {error.message}</div>;
  }

  return (
    <Select.Root value={[displayValue]} collection={data} size="sm" width="320px" onValueChange={localOnValueChange}>
      <Select.HiddenSelect />
      <Select.Label>{label}</Select.Label>
      <Select.Control>
        <Select.Trigger>
          <Select.ValueText placeholder={placeholder} />
        </Select.Trigger>
        <Select.IndicatorGroup>
          {isLoading && (
            <Spinner size="xs" borderWidth="1.5px" color="fg.muted" />
          )}
          <Select.Indicator />
        </Select.IndicatorGroup>
      </Select.Control>
      <Portal>
        <Select.Positioner>
          <Select.Content>
            {data && data.items.map((id) => (
                <Select.Item item={id} key={itemToKey(id)}>
                    {itemToString(id)}
                    <Select.ItemIndicator />
                </Select.Item>
                ))}
          </Select.Content>
        </Select.Positioner>
      </Portal>
    </Select.Root>
  )
}

export default FetchDropdown;