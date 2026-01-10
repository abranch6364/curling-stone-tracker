import { useState, useRef } from "react";
import { HStack, Slider, Button } from "@chakra-ui/react";

const AnimationSlider = ({
  sliderTime,
  onSliderTimeChange,
  animationRunning,
  onAnimationRunningChange,
  sliderMin = 0,
  sliderMax = 0,
  stepSize = 0.25,
}) => {
  const [localSliderTime, setLocalSliderTime] = useState(0);
  const [localAnimationRunning, setLocalAnimationRunning] = useState(false);
  const intervalRef = useRef(null); // Ref to store the interval ID

  const displaySliderTime = sliderTime !== undefined ? sliderTime : localSliderTime;
  const isAnimationRunning = animationRunning !== undefined ? animationRunning : localAnimationRunning;

  //////////////////
  //Helper Functions
  //////////////////

  const updateSliderTime = (newTime) => {
    setLocalSliderTime(newTime);

    if (onSliderTimeChange !== undefined) {
      onSliderTimeChange(newTime);
    }
  };

  const updateAnimationRunning = (isRunning) => {
    setLocalAnimationRunning(isRunning);

    if (onAnimationRunningChange !== undefined) {
      onAnimationRunningChange(isRunning);
    }
  };

  ///////////
  //Callbacks
  ///////////

  const onPlayToggle = () => {
    if (isAnimationRunning) {
      updateAnimationRunning(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    } else {
      updateAnimationRunning(true);
      const startTime = Date.now();
      const startSliderTime = displaySliderTime;

      intervalRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000; // Convert to seconds
        const newSliderTime = startSliderTime + elapsed;
        if (newSliderTime >= sliderMax) {
          updateSliderTime(sliderMax);
          updateAnimationRunning(false);
          clearInterval(intervalRef.current);
        } else {
          updateSliderTime(newSliderTime);
        }
      }, 50); // Update every 50ms for smooth animation
    }
  };

  return (
    <HStack width="100%">
      <Slider.Root
        width="100%"
        min={sliderMin}
        max={sliderMax}
        step={stepSize}
        onValueChange={(e) => updateSliderTime(e.value[0])}
        value={[displaySliderTime]}
      >
        <HStack justify="space-between">
          <Slider.Label>Time</Slider.Label>
          <Slider.ValueText />
        </HStack>
        <Slider.Control>
          <Slider.Track>
            <Slider.Range />
          </Slider.Track>
          <Slider.Thumbs />
        </Slider.Control>
      </Slider.Root>
      <Button onClick={onPlayToggle}>{isAnimationRunning ? "Pause" : "Play"}</Button>
    </HStack>
  );
};

export default AnimationSlider;
