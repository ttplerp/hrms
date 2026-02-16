// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Feedback', {
	onload: function(frm) {
		frm.add_fetch("training_event", "course", "course");
		frm.add_fetch("training_event", "event_name", "event_name");
		frm.add_fetch("training_event", "trainer_name", "trainer_name");

		// Add CSS styles when form loads
		addRatingStyles();
	},

	refresh: function(frm) {
		// Initialize rating scales when form loads
		initializeRatingScale(frm);
		initializeRadioRatings(frm);

		// Disable radio buttons if document is submitted
		if (frm.doc.docstatus !== 0) {
			disableRatingUI();
		}
	},

	length_of_course_rating: function(frm) {
		// Update UI when field value changes programmatically
		updateRatingUI(frm.doc.length_of_course_rating);
	},

	content_rating: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('content_rating', frm.doc.content_rating);
	},

	materials_rating: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('materials_rating', frm.doc.materials_rating);
	},

	ability_to_hold_interest_rating: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('ability_to_hold_interest_rating', frm.doc.ability_to_hold_interest_rating);
	},

	use_of_relevant_examples: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('use_of_relevant_examples', frm.doc.use_of_relevant_examples);
	},
	
	audio_visual: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('audio_visual', frm.doc.audio_visual);
	},

	pace_of_course_was_comfortable: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('pace_of_course_was_comfortable', frm.doc.pace_of_course_was_comfortable);
	},

	usefulness_of_ideas_and_skills_presented: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('usefulness_of_ideas_and_skills_presented', frm.doc.usefulness_of_ideas_and_skills_presented);
	},

	i_would_recommend_this_training: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('i_would_recommend_this_training', frm.doc.i_would_recommend_this_training);
	},

	overall_course_rating: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('overall_course_rating', frm.doc.overall_course_rating);
	},

	ability_to_hold_interest_faci: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('ability_to_hold_interest_faci', frm.doc.ability_to_hold_interest_faci);
	},

	expertise_on_the_topic: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('expertise_on_the_topic', frm.doc.expertise_on_the_topic);
	},

	effective_response_to_questions: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('effective_response_to_questions', frm.doc.effective_response_to_questions);
	},

	ability_to_stay_focused_on_the_topic: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('ability_to_stay_focused_on_the_topic', frm.doc.ability_to_stay_focused_on_the_topic);
	},

	use_of_relevant_examples_faci: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('use_of_relevant_examples_faci', frm.doc.use_of_relevant_examples_faci);
	},

	encouraged_audience_interaction: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('encouraged_audience_interaction', frm.doc.encouraged_audience_interaction);
	},

	seriousness_on_attendance: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('seriousness_on_attendance', frm.doc.seriousness_on_attendance);
	},

	overall_facilitator_rating: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('overall_facilitator_rating', frm.doc.overall_facilitator_rating);
	},

	seating_comfort: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('seating_comfort', frm.doc.seating_comfort);
	},

	room_temperature: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('room_temperature', frm.doc.room_temperature);
	},

	room_lighting: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('room_lighting', frm.doc.room_lighting);
	},

	food: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('food', frm.doc.food);
	},

	overall_logistics_arrangement: function(frm) {
		// Update UI when field value changes programmatically
		updateRadioUI('overall_logistics_arrangement', frm.doc.overall_logistics_arrangement);
	},
	hr_travel_itinerary_timely(frm) {
		updateRadioUI('hr_travel_itinerary_timely', frm.doc.hr_travel_itinerary_timely);
	},
	hr_clarification_clear(frm) {
		updateRadioUI('hr_clarification_clear', frm.doc.hr_clarification_clear);
	},
	hr_clarification_prompt(frm) {
		updateRadioUI('hr_clarification_prompt', frm.doc.hr_clarification_prompt);
	},
	hr_nomination_fair(frm) {
		updateRadioUI('hr_nomination_fair', frm.doc.hr_nomination_fair);
	},

});

// Global function to set rating value (for circle ratings)
function setRating(value) {
	// Remove selected class from all options
	document.querySelectorAll('.rating-circle').forEach(circle => {
		circle.classList.remove('selected');
	});
	
	// Add selected class to clicked option
	const selectedCircle = document.querySelector(`[data-value='${value}']`);
	if (selectedCircle) {
		selectedCircle.classList.add('selected');
	}
	
	// Set the field value using Frappe's model
	frappe.model.set_value(cur_frm.doctype, cur_frm.docname, 'length_of_course_rating', value);
}

// Global function to set radio rating value
function setRadioRating(fieldName, value) {
	// Set the field value using Frappe's model
	frappe.model.set_value(cur_frm.doctype, cur_frm.docname, fieldName, value);
}

// Initialize rating scale UI (for circle ratings)
function initializeRatingScale(frm) {
	// Wait for DOM to be ready
	setTimeout(() => {
		const ratingCircles = document.querySelectorAll('.rating-circle');
		if (ratingCircles.length > 0) {
			// Add click event listeners to each rating circle
			ratingCircles.forEach(circle => {
				circle.addEventListener('click', function() {
					const value = this.getAttribute('data-value');
					setRating(value);
				});
			});
			
			// Set initial state if value exists
			if (frm.doc.length_of_course_rating) {
				updateRatingUI(frm.doc.length_of_course_rating);
			}

			// Disable rating circles if document is submitted
			if (frm.doc.docstatus !== 0) {
				disableRatingCircles();
			}
		}
	}, 100);
}

// Initialize radio rating UI
function initializeRadioRatings(frm) {
	// Wait for DOM to be ready
	setTimeout(() => {
		// Add event listeners for content rating
		const contentRadios = document.querySelectorAll('input[name="content_rating"]');
		contentRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('content_rating', this.value);
				}
			});
		});

		// Add event listeners for Materials
		const materialsRadios = document.querySelectorAll('input[name="materials_rating"]');
		materialsRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('materials_rating', this.value);
				}
			});
		});

		// Add event listeners for ability to hold interest rating
		const abilityRadios = document.querySelectorAll('input[name="ability_to_hold_interest_rating"]');
		abilityRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('ability_to_hold_interest_rating', this.value);
				}
			});
		});
		
		// Add event listeners for Use of relevant examples
		const relevantExampleRadios = document.querySelectorAll('input[name="use_of_relevant_examples"]');
		relevantExampleRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('use_of_relevant_examples', this.value);
				}
			});
		});
		
		// Add event listeners for Audio/Visual
		const audioVisualRadios = document.querySelectorAll('input[name="audio_visual"]');
		audioVisualRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('audio_visual', this.value);
				}
			});
		});
		
		// Add event listeners for Place Of course was comfortable
		const placeOfCourseRadios = document.querySelectorAll('input[name="pace_of_course_was_comfortable"]');
		placeOfCourseRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('pace_of_course_was_comfortable', this.value);
				}
			});
		});
		
		// Add event listeners for Usefulness of ideas and skills presented
		const usefulnessRadios = document.querySelectorAll('input[name="usefulness_of_ideas_and_skills_presented"]');
		usefulnessRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('usefulness_of_ideas_and_skills_presented', this.value);
				}
			});
		});
		
		// Add event listeners for recommend this training
		const recommendRadios = document.querySelectorAll('input[name="i_would_recommend_this_training"]');
		recommendRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('i_would_recommend_this_training', this.value);
				}
			});
		});
		
		// Add event listeners for overall course rating
		const overallRatingRadios = document.querySelectorAll('input[name="overall_course_rating"]');
		overallRatingRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('overall_course_rating', this.value);
				}
			});
		});
		
		// ##################################################################
		// Add event listeners for Hold interest for facilitator
		const facilitatorInterestRadios = document.querySelectorAll('input[name="ability_to_hold_interest_faci"]');
		facilitatorInterestRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('ability_to_hold_interest_faci', this.value);
				}
			});
		});
		
		// Add event listeners for Expertise on the Topic
		const expertiseRadios = document.querySelectorAll('input[name="expertise_on_the_topic"]');
		expertiseRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('expertise_on_the_topic', this.value);
				}
			});
		});
		
		// Add event listeners for Effective response to questions
		const effectiveResponseRadios = document.querySelectorAll('input[name="effective_response_to_questions"]');
		effectiveResponseRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('effective_response_to_questions', this.value);
				}
			});
		});
		
		// Add event listeners for Ability to stay focused on the topic
		const stayFocusRadios = document.querySelectorAll('input[name="ability_to_stay_focused_on_the_topic"]');
		stayFocusRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('ability_to_stay_focused_on_the_topic', this.value);
				}
			});
		});
		
		// Add event listeners for Use of relevant examples by facilitator
		const relevantExampleFaciRadios = document.querySelectorAll('input[name="use_of_relevant_examples_faci"]');
		relevantExampleFaciRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('use_of_relevant_examples_faci', this.value);
				}
			});
		});
		
		// Add event listeners for Encouraged audience interaction
		const encourageRadios = document.querySelectorAll('input[name="encouraged_audience_interaction"]');
		encourageRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('encouraged_audience_interaction', this.value);
				}
			});
		});
		
		// Add event listeners for Seriousness on attendance
		const attendanceRadios = document.querySelectorAll('input[name="seriousness_on_attendance"]');
		attendanceRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('seriousness_on_attendance', this.value);
				}
			});
		});
		
		// Add event listeners for Facilitator rating
		const facilitatorRadios = document.querySelectorAll('input[name="overall_facilitator_rating"]');
		facilitatorRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('overall_facilitator_rating', this.value);
				}
			});
		});
		
		// #######################################################3
		// Add event listeners for Seating comfort
		const seatingRadios = document.querySelectorAll('input[name="seating_comfort"]');
		seatingRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('seating_comfort', this.value);
				}
			});
		});
		
		// Add event listeners for Room Temp
		const roomTempRadios = document.querySelectorAll('input[name="room_temperature"]');
		roomTempRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('room_temperature', this.value);
				}
			});
		});
		
		// Add event listeners for root lighting
		const lightingRadios = document.querySelectorAll('input[name="room_lighting"]');
		lightingRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('room_lighting', this.value);
				}
			});
		});
		
		// Add event listeners for Food
		const foodRadios = document.querySelectorAll('input[name="food"]');
		foodRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('food', this.value);
				}
			});
		});
		
		// Add event listeners for Logistics
		const logisticsRadios = document.querySelectorAll('input[name="overall_logistics_arrangement"]');
		logisticsRadios.forEach(radio => {
			radio.addEventListener('change', function() {
				if (this.checked) {
					setRadioRating('overall_logistics_arrangement', this.value);
				}
			});
		});

		//hr
		[
		'hr_travel_itinerary_timely',
		'hr_clarification_clear',
		'hr_clarification_prompt',
		'hr_nomination_fair'
		].forEach(field => {
			document.querySelectorAll(`input[name="${field}"]`).forEach(radio => {
				radio.addEventListener('change', function () {
					if (this.checked) {
						setRadioRating(field, this.value);
					}
				});
			});

			if (frm.doc[field]) {
				updateRadioUI(field, frm.doc[field]);
			}
		});


		// Set initial states if values exist
		if (frm.doc.content_rating) {
			updateRadioUI('content_rating', frm.doc.content_rating);
		}
		if (frm.doc.materials_rating) {
			updateRadioUI('materials_rating', frm.doc.materials_rating);
		}
		if (frm.doc.ability_to_hold_interest_rating) {
			updateRadioUI('ability_to_hold_interest_rating', frm.doc.ability_to_hold_interest_rating);
		}
		if (frm.doc.use_of_relevant_examples) {
			updateRadioUI('use_of_relevant_examples', frm.doc.use_of_relevant_examples);
		}
		if (frm.doc.audio_visual) {
			updateRadioUI('audio_visual', frm.doc.audio_visual);
		}
		if (frm.doc.pace_of_course_was_comfortable) {
			updateRadioUI('pace_of_course_was_comfortable', frm.doc.pace_of_course_was_comfortable);
		}
		if (frm.doc.usefulness_of_ideas_and_skills_presented) {
			updateRadioUI('usefulness_of_ideas_and_skills_presented', frm.doc.usefulness_of_ideas_and_skills_presented);
		}
		if (frm.doc.i_would_recommend_this_training) {
			updateRadioUI('i_would_recommend_this_training', frm.doc.i_would_recommend_this_training);
		}
		if (frm.doc.overall_course_rating) {
			updateRadioUI('overall_course_rating', frm.doc.overall_course_rating);
		}
		if (frm.doc.ability_to_hold_interest_faci) {
			updateRadioUI('ability_to_hold_interest_faci', frm.doc.ability_to_hold_interest_faci);
		}
		if (frm.doc.expertise_on_the_topic) {
			updateRadioUI('expertise_on_the_topic', frm.doc.expertise_on_the_topic);
		}
		if (frm.doc.effective_response_to_questions) {
			updateRadioUI('effective_response_to_questions', frm.doc.effective_response_to_questions);
		}
		if (frm.doc.ability_to_stay_focused_on_the_topic) {
			updateRadioUI('ability_to_stay_focused_on_the_topic', frm.doc.ability_to_stay_focused_on_the_topic);
		}
		if (frm.doc.use_of_relevant_examples_faci) {
			updateRadioUI('use_of_relevant_examples_faci', frm.doc.use_of_relevant_examples_faci);
		}
		if (frm.doc.encouraged_audience_interaction) {
			updateRadioUI('encouraged_audience_interaction', frm.doc.encouraged_audience_interaction);
		}
		if (frm.doc.seriousness_on_attendance) {
			updateRadioUI('seriousness_on_attendance', frm.doc.seriousness_on_attendance);
		}
		if (frm.doc.overall_facilitator_rating) {
			updateRadioUI('overall_facilitator_rating', frm.doc.overall_facilitator_rating);
		}
		if (frm.doc.seating_comfort) {
			updateRadioUI('seating_comfort', frm.doc.seating_comfort);
		}
		if (frm.doc.room_temperature) {
			updateRadioUI('room_temperature', frm.doc.room_temperature);
		}
		if (frm.doc.room_lighting) {
			updateRadioUI('room_lighting', frm.doc.room_lighting);
		}
		if (frm.doc.food) {
			updateRadioUI('food', frm.doc.food);
		}
		if (frm.doc.overall_logistics_arrangement) {
			updateRadioUI('overall_logistics_arrangement', frm.doc.overall_logistics_arrangement);
		}

		// Disable radio buttons if document is submitted
		if (frm.doc.docstatus !== 0) {
			disableRadioRatings();
		}
	}, 100);
}

// Update rating UI based on current value (for circle ratings)
function updateRatingUI(value) {
	if (value) {
		document.querySelectorAll('.rating-circle').forEach(circle => {
			circle.classList.remove('selected');
		});
		
		const selectedCircle = document.querySelector(`[data-value='${value}']`);
		if (selectedCircle) {
			selectedCircle.classList.add('selected');
		}
	}
}

// Update radio UI based on current value
function updateRadioUI(fieldName, value) {
	if (value) {
		const radio = document.querySelector(`input[name="${fieldName}"][value="${value}"]`);
		if (radio) {
			radio.checked = true;
		}
	}
}

// Add CSS styles dynamically
function addRatingStyles() {
	// Check if styles already exist to avoid duplicates
	if (document.getElementById('training-feedback-rating-styles')) {
		return;
	}
	
	const style = document.createElement('style');
	style.id = 'training-feedback-rating-styles';
	style.textContent = `
		/* Circle Rating Styles */
		.rating-scale {
			margin: 0px 0 30px 0;
		}
		
		.rating-question {
			font-weight: bold;
			margin-bottom: 10px;
			font-size: 14px;
		}
		
		.rating-container {
			display: flex;
			align-items: center;
			gap: 15px;
		}
		
		.rating-label {
			font-size: 12px;
			color: #666;
		}
		
		.rating-options {
			display: flex;
			gap: 20px;
			align-items: center;
		}
		
		.rating-circle {
			width: 20px;
			height: 20px;
			border: 2px solid #ddd;
			border-radius: 50%;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 12px;
			font-weight: 500;
			transition: all 0.2s ease;
			cursor: pointer;
		}
		
		// .rating-circle:hover {
		// 	border-color: #007bff;
		// 	background-color: #f8f9fa;
		// }
		
		.rating-circle.selected {
			border-color: #007bff;
			background-color: #007bff;
			color: white;
		}

		/* Radio Rating Styles */
		.radio-rating-scale {
			margin: 0px 0 30px 0;
			padding: 0px 0;
			border-bottom: 1px solid #e9ecef;
		}
		
		.radio-rating-scale:last-child {
			border-bottom: none;
		}
		
		.radio-options {
			display: flex;
			flex-direction: column;
			gap: 2px;
			margin-top: 0px;
		}
		
		.radio-option {
			display: flex;
			align-items: center;
			cursor: pointer;
			padding: 5px 0;
		}
		
		.rating-radio {
			margin-right: 10px;
			width: 16px;
			height: 14px;
			cursor: pointer;
		}
		
		.radio-label {
			font-size: 14px;
			color: #333;
			cursor: pointer;
		}
		
		// .radio-option:hover .radio-label {
		// 	color: #007bff;
		// }
		
		// .rating-radio:checked + .radio-label {
		// 	color: #007bff;
		// 	font-weight: 500;
		// }
	`;
	document.head.appendChild(style);
}

// Disable radio ratings when document is submitted
function disableRadioRatings() {
	// Disable content rating radios
	const contentRadios = document.querySelectorAll('input[name="content_rating"]');
	contentRadios.forEach(radio => {
		radio.disabled = true;
	});

	const materialsRadios = document.querySelectorAll('input[name="materials_rating"]');
	materialsRadios.forEach(radio => {
		radio.disabled = true;
	});

	
	// Disable ability to hold interest rating radios
	const abilityRadios = document.querySelectorAll('input[name="ability_to_hold_interest_rating"]');
	abilityRadios.forEach(radio => {
		radio.disabled = true;
	});

	// Add event listeners for Use of relevant examples
	const relevantExampleRadios = document.querySelectorAll('input[name="use_of_relevant_examples"]');
	relevantExampleRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Audio/Visual
	const audioVisualRadios = document.querySelectorAll('input[name="audio_visual"]');
	audioVisualRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Place Of course was comfortable
	const placeOfCourseRadios = document.querySelectorAll('input[name="pace_of_course_was_comfortable"]');
	placeOfCourseRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Usefulness of ideas and skills presented
	const usefulnessRadios = document.querySelectorAll('input[name="usefulness_of_ideas_and_skills_presented"]');
	usefulnessRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for recommend this training
	const recommendRadios = document.querySelectorAll('input[name="i_would_recommend_this_training"]');
	recommendRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for overall course rating
	const overallRatingRadios = document.querySelectorAll('input[name="overall_course_rating"]');
	overallRatingRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// ##################################################################
	// Add event listeners for Hold interest for facilitator
	const facilitatorInterestRadios = document.querySelectorAll('input[name="ability_to_hold_interest_faci"]');
	facilitatorInterestRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Expertise on the Topic
	const expertiseRadios = document.querySelectorAll('input[name="expertise_on_the_topic"]');
	expertiseRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Effective response to questions
	const effectiveResponseRadios = document.querySelectorAll('input[name="effective_response_to_questions"]');
	effectiveResponseRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Ability to stay focused on the topic
	const stayFocusRadios = document.querySelectorAll('input[name="ability_to_stay_focused_on_the_topic"]');
	stayFocusRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Use of relevant examples by facilitator
	const relevantExampleFaciRadios = document.querySelectorAll('input[name="use_of_relevant_examples_faci"]');
	relevantExampleFaciRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Encouraged audience interaction
	const encourageRadios = document.querySelectorAll('input[name="encouraged_audience_interaction"]');
	encourageRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Seriousness on attendance
	const attendanceRadios = document.querySelectorAll('input[name="seriousness_on_attendance"]');
	attendanceRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Facilitator rating
	const facilitatorRadios = document.querySelectorAll('input[name="overall_facilitator_rating"]');
	facilitatorRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// #######################################################3
	// Add event listeners for Seating comfort
	const seatingRadios = document.querySelectorAll('input[name="seating_comfort"]');
	seatingRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Room Temp
	const roomTempRadios = document.querySelectorAll('input[name="room_temperature"]');
	roomTempRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for root lighting
	const lightingRadios = document.querySelectorAll('input[name="room_lighting"]');
	lightingRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Food
	const foodRadios = document.querySelectorAll('input[name="food"]');
	foodRadios.forEach(radio => {
		radio.disabled = true;
	});
	
	// Add event listeners for Logistics
	const logisticsRadios = document.querySelectorAll('input[name="overall_logistics_arrangement"]');
	logisticsRadios.forEach(radio => {
		radio.disabled = true;
	});

	//hr
	[
	'hr_travel_itinerary_timely',
	'hr_clarification_clear',
	'hr_clarification_prompt',
	'hr_nomination_fair'
	].forEach(field => {
		document.querySelectorAll(`input[name="${field}"]`)
			.forEach(radio => radio.disabled = true);
	});

}

// Disable rating circles when document is submitted
function disableRatingCircles() {
	const ratingCircles = document.querySelectorAll('.rating-circle');
	ratingCircles.forEach(circle => {
		circle.style.pointerEvents = 'none';
		circle.style.opacity = '0.6';
		circle.style.cursor = 'not-allowed';
	});
}

// Disable all rating UI when document is submitted
function disableRatingUI() {
	disableRadioRatings();
	disableRatingCircles();
}