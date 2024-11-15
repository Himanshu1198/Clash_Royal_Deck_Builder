import { useState } from 'react'
import axios from 'axios'

function App() {
  const [playerId, setPlayerId] = useState('')
  const [cards, setCards] = useState([])
  const [avgElixir, setAvgElixir] = useState(null)

  const onSubmit = async () => {
    try {
      // Make the API request using axios
      const response = await axios.get(
        `http://127.0.0.1:5000/get-deck/${playerId.replace('#', '%23')}`
      )

      if (response.data.status === 'success') {
        // Update the cards state with the deck
        setCards(response.data.deck)
        // Update the average elixir cost state
        setAvgElixir(response.data.avg)
      } else {
        console.error('Error fetching deck data:', response.data.error)
      }
    } catch (error) {
      console.error('Error making API request:', error)
    }

    document
      .getElementsByClassName('container-container')[0]
      .classList.add('container-container-shift')
    setTimeout(() => {
      document
        .getElementsByClassName('cards-container')[0]
        .classList.add('cards-container-shift')
    }, 2000)
  }

  return (
    <>
      <div className='container'>
        <div className='container-container'>
          <div id='player-id-input-container'>
            <input
              id='player-id-input'
              type='text'
              value={playerId}
              onChange={(e) => setPlayerId(e.target.value)}
              placeholder='Enter player id starting with #'
            />
            <button id='submit-button' onClick={onSubmit}>
              Submit
            </button>
          </div>
          {avgElixir !== null && <div>Average Elixir Cost: {avgElixir}</div>}
        </div>
        <div className='cards-container'>
          {cards.map((card) => (
            <div className='card-container' key={card.name}>
              <div className='card-name'>{card.name}</div>
              <div className='card-image-container'>
                <img
                  src={card.icon_url}
                  alt={card.name}
                  className='card-image'
                />
              </div>
              <div className='card-stats'>
                <div className='card-level'>Level: {card.level}</div>
                <div className='card-elixir'>Elixir: {card.elixir_cost}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

export default App
