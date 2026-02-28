import { useState } from "react";
import { HStack, NumberInput, Text, Box } from "@chakra-ui/react";

const TimeInput = ({ onChangeTotalSeconds }) => {
  const [inputHours, setInputHours] = useState(0);
  const [inputMinutes, setInputMinutes] = useState(0);
  const [inputSeconds, setInputSeconds] = useState(0);

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
    <Box border="1px solid #333" padding="5px">
      <HStack>
        <NumberInput.Root width="42px" min={0}>
          <NumberInput.Input value={inputHours} onChange={(e) => onHoursChange(e)} />
        </NumberInput.Root>
        <Text>:</Text>
        <NumberInput.Root width="42px" min={0} max={59}>
          <NumberInput.Input value={inputMinutes} onChange={(e) => onMinutesChange(e)} />
        </NumberInput.Root>
        <Text>:</Text>
        <NumberInput.Root width="42px" min={0} max={59}>
          <NumberInput.Input value={inputSeconds} onChange={(e) => onSecondsChange(e)} />
        </NumberInput.Root>
      </HStack>
    </Box>
  );
};

export default TimeInput;
