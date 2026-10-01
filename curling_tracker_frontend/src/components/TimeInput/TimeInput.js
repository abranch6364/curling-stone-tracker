import { useState } from "react";
import { HStack, NumberInput, Text, Box } from "@chakra-ui/react";

const TimeInput = ({ onChangeTotalSeconds, initialSeconds = 0, disabled = false }) => {
  const [inputHours, setInputHours] = useState(Math.floor(initialSeconds / 3600));
  const [inputMinutes, setInputMinutes] = useState(Math.floor((initialSeconds % 3600) / 60));
  const [inputSeconds, setInputSeconds] = useState(initialSeconds % 60);

  const updateTime = (hours, minutes, seconds) => {
    let totalTime = Number(seconds) + Number(minutes) * 60 + Number(hours) * 3600;
    if (onChangeTotalSeconds !== undefined) {
      onChangeTotalSeconds(totalTime);
    }
  };

  const onHoursChange = (e) => {
    setInputHours(e.target.value);
    updateTime(e.target.value, inputMinutes, inputSeconds);
  };

  const onMinutesChange = (e) => {
    setInputMinutes(e.target.value);
    updateTime(inputHours, e.target.value, inputSeconds);
  };

  const onSecondsChange = (e) => {
    setInputSeconds(e.target.value);
    updateTime(inputHours, inputMinutes, e.target.value);
  };

  return (
    <Box borderWidth="1px" borderColor="border" borderRadius="md" paddingX="1">
      <HStack gap="1">
        <NumberInput.Root size="sm" width="42px" min={0} disabled={disabled}>
          <NumberInput.Input value={inputHours} onChange={(e) => onHoursChange(e)} />
        </NumberInput.Root>
        <Text>:</Text>
        <NumberInput.Root size="sm" width="42px" min={0} max={59} disabled={disabled}>
          <NumberInput.Input value={inputMinutes} onChange={(e) => onMinutesChange(e)} />
        </NumberInput.Root>
        <Text>:</Text>
        <NumberInput.Root size="sm" width="42px" min={0} max={59} disabled={disabled}>
          <NumberInput.Input value={inputSeconds} onChange={(e) => onSecondsChange(e)} />
        </NumberInput.Root>
      </HStack>
    </Box>
  );
};

export default TimeInput;
