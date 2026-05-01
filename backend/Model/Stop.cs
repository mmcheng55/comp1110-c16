using System;
using System.Numerics;
using System.Text.Json.Serialization;

namespace Model
{
    [Serializable]
    public class Stop(string stopName, Vector2 normalizedPositionOnScreen) : IEquatable<Stop>
    {
        [JsonPropertyName("stopName")]
        public string StopName { get; } = stopName;

        /// <summary>
        /// Normalized position on the screen is defined as (0,0) to (1,1). (0,0) is the bottom-left corner of screen, (1,1) is the top-right corner of screen. <br></br>
        /// </summary>
        [JsonPropertyName("normalizedPositionOnScreen")]
        public Vector2 NormalizedPositionOnScreen { get; } = normalizedPositionOnScreen;

        public bool Equals(Stop? other)
        {
            return StopName == other?.StopName;
        }
        
        public override int GetHashCode()
        {
            return HashCode.Combine(StopName);
        }
    }
}